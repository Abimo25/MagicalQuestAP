# ==============
# = SNI Client =
# ==============

# - STATELESS INVARIANTS (re-evaluated at every poll from the item history alone, so if the player resets, does a savestate load or a
#   reconnect, it repairs itself): Map Fragments ($7FEE00), Pete's Emblem count ($7FEE0D), the checked Store Locations
#   ($7FEE18), Max Health, the two Upgrade flags, the Costume flags.
# - ONE-SHOT EFFECTS (coins, refills, Small Heart, Mickey Doll, the Big Heart heal) are applied once, in order, driven by
#   the received-item index in AP RAM ($7FEE02-$7FEE03). The index lives in the game's RAM on purpose: a New Game
#   zeroes it and the history is replayed, a savestate load restores it together with the state it belongs to. It only
#   advances while the safety gate is open, so no item is ever lost, only delayed.
# - JINGLES: when the dispatcher passes Items that arrived after the client connected, it asks
#   the ROM for one jingle per poll, the Costume jingle if a Costume is among them, otherwise the general one (Filler stays silent). The
#   history already there at connect, and any replay (New Game, savestate load), stays silent.
# - MESSAGES: the same new Items, plus Items this slot sends, become in-game messages
#   ("RECEIVED X" / "FROM PLAYER"). They queue in the client; the next one is written to AP RAM when the ROM is idle.
#   Nothing shows on the World Map (its text rows hold the Level Select); messages wait for a Level.
# - The AP block is ignored until the ROM has marked it valid ($7FEE1C-$7FEE1F = "MQOK"): bank $7F is not cleared at boot,
#   so before the title screen it is garbage and triggers a bunch of fake Location checks without this patch.
# - The client never writes $02BD (the vanilla game uses this as a failsafe to stop the player from grabbing multiple Big Hearts).
# - Locations are detected from the ROM latches ($7FEE10-$7FEE15, the Store latch $7FEE17) and from vanilla RAM (Area,
#   Stage, Level, $1D8D).
# - LEVELS PLAYED (the Level Select): the ROM records them in AP RAM ($7FEEE0-$7FEEE6), which a power cycle clears (the
#   cartridge has no save RAM). The client keeps a copy in the server's data storage (key levels_key(), one integer,
#   byte n = Stage Index n) and every poll writes RAM | server back to RAM and sends new bits with an "or" Set.
#   Bits are only ever added.

import logging
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from NetUtils import ClientStatus
from worlds.AutoSNIClient import SNIClient

from . import Messages, Ram, RomData, TrackerData
from .data import items_data
from .data.items_data import STARTING_ID
from .data.locations_data import LOCATIONS
from .names import GAME_NAME, WORLD_VERSION
from .names import item_name as I

snes_logger = logging.getLogger("SNES")

# ---- What one poll reads ---------------------------------------------------------------------------------
# Block A: $7E02A8-$7E037E holds the coins, Stage/Level/Area, Max Health ... the Big Heart lock, the Pause flag
# ($0343), Lives ($0372) and the HUD flags ($0378-$037E), in one SNI read. Plus $1D8D and the AP block.
BLOCK_BASE = Ram.COINS_HUNDREDS
BLOCK_END = Ram.HUD_METERS
BLOCK_LENGTH = BLOCK_END - BLOCK_BASE + 1
IDENTITY_LENGTH = RomData.SLOT_NAME_LENGTH + RomData.SEED_NAME_LENGTH
MAX_ITEMS_PER_POLL = 32
GOAL_TEXT = "Saved Pluto!"

# ---- Item and Location lookup tables, built from the data tables ---------------------------------------------
ITEM_EFFECT: Dict[int, Tuple] = {STARTING_ID + item.id_offset: item.effect for item in items_data.ITEMS}
ITEM_ID: Dict[str, int] = {item.name: STARTING_ID + item.id_offset for item in items_data.ITEMS}
BIG_HEART_ID = ITEM_ID[I.big_heart]
FILLER_IDS = {ITEM_ID[name] for name in items_data.FILLER_ITEMS}
EMBLEM_ID = ITEM_ID[I.petes_emblem]
MAX_HEALTH_CAP = 10

COSTUME_FLAGS = (Ram.COSTUME_WIZARD, Ram.COSTUME_FIREFIGHTER, Ram.COSTUME_MOUNTAINEER)
UPGRADE_ITEM = {Ram.WIZARD_UPGRADE: ITEM_ID[I.magic_upgrade], Ram.FIREFIGHTER_UPGRADE: ITEM_ID[I.water_upgrade]}
# Progressive Costumes option: item ID -> (Costume flag, Upgrade flag); 1 copy owns the Costume, 2 its Upgrade too
PROGRESSIVE_ITEM: Dict[int, Tuple[int, int]] = {i: (e[1], e[2]) for i, e in ITEM_EFFECT.items() if e[0] == "progressive"}


def progressive_flags(items: List[int], copies: int) -> Set[int]:
    # The Costume flags (copies = 1) or the Upgrade flags (copies = 2) owned through progressive items.
    return {flags[copies - 1] for item_id, flags in PROGRESSIVE_ITEM.items() if items.count(item_id) >= copies}


def _index(kind: str) -> Dict[Tuple, int]:
    # Detect-key tail -> Location ID, for every Location of one detection kind.
    return {loc.detect[1:]: STARTING_ID + loc.id_offset for loc in LOCATIONS if loc.detect[0] == kind}


BOX_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("box").items()}               # latch bit number -> ID
ODD_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("odd").items()}               # mask in $7FEE15 -> ID
CLEAR_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("stage_clear").items()}     # Stage Index -> ID
BOSS_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("boss").items()}
_MINI = _index("mini_boss")
MINI_BOSS_IDS: Dict[Tuple[int, int], int] = {level: _MINI[(level[0],)] for level in Ram.MINI_BOSS_LEVELS}   # (Stage, Level)
REMATCH_IDS: Dict[Tuple[int, int], int] = _index("rematch")                                                 # (6, Level)
_ENTRY = _index("costume_entry")
COSTUME_ENTRY_IDS: Dict[Tuple[int, int, int], int] = {                                       # (Stage, Level, Area)
    entry: _ENTRY[(entry[0],)] for entry in Ram.COSTUME_ENTRY_LEVELS.values()}
_STORE = _index("store")                                                                       # (mask, Area) -> ID
STORE_IDS: Dict[int, int] = {key[0]: lid for key, lid in _STORE.items()}                       # mask in $7FEE17 -> ID
STORE_HEART_IDS: Dict[int, int] = {key[1]: lid for key, lid in _STORE.items() if key[1]}       # selling Store Area -> ID
UPGRADE_IDS: Tuple[int, ...] = tuple(lid for key, lid in _STORE.items() if not key[1])         # sold in every Store


def detectable_ids() -> Set[int]:
    # Every Location ID the Tracker can report (the test checks this is every Location of the world).
    ids: Set[int] = set(BOX_IDS.values()) | set(ODD_IDS.values()) | set(CLEAR_IDS.values()) | set(BOSS_IDS.values())
    ids |= set(MINI_BOSS_IDS.values()) | set(REMATCH_IDS.values()) | set(COSTUME_ENTRY_IDS.values())
    ids |= set(STORE_IDS.values())
    return ids


# ---- Memory view ----------------------------------------------------------------------------------------------
class Memory:
    # The WRAM of one poll, addressed by CPU address ($7E....). "set" stages a write and updates the view, so
    # several effects in one poll see each other's results. "writes()"" returns the staged bytes as SNI runs.
    def __init__(self, block: bytes, boss_flag: int, ap_block: bytes):
        if len(block) != BLOCK_LENGTH or len(ap_block) != Ram.AP_BLOCK_SIZE:
            raise ValueError("unexpected read size")
        self._block = bytearray(block)
        self._boss = boss_flag
        self._ap = bytearray(ap_block)
        self._staged: Dict[int, int] = {}

    def _cell(self, address: int) -> Tuple[bytearray, int]:
        if BLOCK_BASE <= address <= BLOCK_END:
            return self._block, address - BLOCK_BASE
        if Ram.AP_BLOCK <= address < Ram.AP_BLOCK + Ram.AP_BLOCK_SIZE:
            return self._ap, address - Ram.AP_BLOCK
        raise KeyError(f"address ${address:06X} is not part of the poll")

    def get(self, address: int) -> int:
        if address == Ram.BOSS_FLAG:
            return self._boss
        cell, offset = self._cell(address)
        return cell[offset]

    def set(self, address: int, value: int) -> None:
        if address == Ram.BOSS_FLAG:
            raise KeyError("the boss flag is read only")
        value &= 0xFF
        cell, offset = self._cell(address)
        if cell[offset] != value:
            cell[offset] = value
            self._staged[address] = value

    def bump(self, address: int) -> None:
        # Increment this so the game redraws that UI element.
        self.set(address, self.get(address) + 1)

    def get16(self, address: int) -> int:
        return self.get(address) | (self.get(address + 1) << 8)

    def set16(self, address: int, value: int) -> None:
        self.set(address, value & 0xFF)
        self.set(address + 1, (value >> 8) & 0xFF)

    def writes(self) -> List[Tuple[int, bytes]]:
        # [(SNI address, data)] with consecutive bytes merged.
        runs: List[Tuple[int, bytearray]] = []
        for address in sorted(self._staged):
            if runs and runs[-1][0] + len(runs[-1][1]) == address:
                runs[-1][1].append(self._staged[address])
            else:
                runs.append((address, bytearray([self._staged[address]])))
        return [(Ram.wram(address), bytes(data)) for address, data in runs]


class TickResult(NamedTuple):
    locations: List[int]         # newly detected Location IDs (for anything I may have missed).
    goal: bool                   # Emperor Pete defeated.
    levels: Optional[int] = None  # Levels played to save on the server ("or"), when RAM has bits the server lacks
    scout: Tuple[int, ...] = ()  # Store Locations to send as hints, once each per connection (so the player can know what is actually in the Store before purchasing a Location check).


# ---- The logic ------------------------------------------------------------------------------------------------
class Tracker:
    def __init__(self, starting_max_health: int):
        self.starting_max_health = max(1, min(MAX_HEALTH_CAP, starting_max_health))
        self.store_hints = True
        self.item_messages = "all"                                  # Messages.MODES
        self.describe = None                                       # item index -> Messages.Message (set by the glue)
        self.levels_saved: Optional[int] = None                    # the server's Levels played (None = not received yet)
        self.reset()

    def reset(self) -> None:
        # Basically, forget everything seen in RAM (a new ROM, a reconnect). The edge detectors need one poll to arm again.
        self.prev_boss_bit: Optional[int] = None
        self.prev_paused = 0
        self.battle_context: Optional[Tuple[int, int]] = None      # (Stage, Level) seen during the boss battle.
        self.died_in_battle = False
        self.battle_quit_count: Optional[int] = None
        self.map_seen = False                                      # the World Map was seen since the last title/intro.
        self.warned_costumes: Set[int] = set()
        self.hinted: Set[int] = set()                              # Store Locations already sent as hints.
        self.jingle_from: Optional[int] = None                     # first item index that may play a jingle
        self.notices = Messages.MessageQueue()                     # in-game messages waiting to be shown
        self.messages: List[str] = []

    # ---- derived from the item history ----
    def true_max_health(self, items: List[int]) -> int:
        return min(MAX_HEALTH_CAP, self.starting_max_health + items.count(BIG_HEART_ID))

    @staticmethod
    def safe_to_write(mem: Memory) -> bool:
        if mem.get(Ram.PAUSED) != 0:
            return False
        area = mem.get(Ram.AREA)
        if area == Ram.AREA_TRANSIT_OR_5_1 and (mem.get(Ram.STAGE_INDEX), mem.get(Ram.LEVEL_INDEX)) == Ram.LEVEL_5_1:
            return True
        return area not in Ram.AREA_NO_WRITE

    # ---- one poll ----
    def tick(self, mem: Memory, items: List[int], known: Set[int]) -> TickResult:
        new: List[int] = []
        if bytes(mem.get(Ram.AP_MAGIC + i) for i in range(len(Ram.AP_MAGIC_VALUE))) != Ram.AP_MAGIC_VALUE:
            # The title init has not cleared the AP block yet (power-on garbage): read nothing, write nothing, and
            # forget the edge detectors so they arm again on clean data.
            self.reset()
            return TickResult(new, False)
        if self.jingle_from is None:
            self.jingle_from = len(items)                          # what is already received at connect is silent

        def report(location_id: int) -> None:
            if location_id not in known and location_id not in new:
                new.append(location_id)

        goal = self.detect_locations(mem, report)
        self.upgrade_invariant(mem, items)
        self.mirror_to_ap_ram(mem, items, known)
        self.tracker_counts(mem, items, known)
        self.max_health_invariant(mem, items)
        levels = self.levels_played(mem)
        if self.safe_to_write(mem):
            self.costume_invariant(mem, items)
            self.dispatch(mem, items)
            self.show_notice(mem)
        return TickResult(new, goal, levels, self.store_hint_ids(mem, known))

    def store_hint_ids(self, mem: Memory, known: Set[int]) -> Tuple[int, ...]:
        # Inside a Store: the Locations to hint. The Upgrades are the same Location in every Store; the Big Heart only in its own Store (patched so every Store sells one).
        # Each is sent once per connection, and never when already checked.
        # The server's own 'only new' rule keeps a repeat after a reconnect from making a duplicate hint.
        area = mem.get(Ram.AREA)
        if not self.store_hints or area not in Ram.STORE_AREAS:
            return ()
        wanted = list(UPGRADE_IDS)
        if area in STORE_HEART_IDS:
            wanted.append(STORE_HEART_IDS[area])
        fresh = tuple(i for i in wanted if i not in self.hinted and i not in known)
        self.hinted.update(fresh)
        return fresh

    # ---- Location detection ----
    def detect_locations(self, mem: Memory, report) -> bool:
        stage, level, area = mem.get(Ram.STAGE_INDEX), mem.get(Ram.LEVEL_INDEX), mem.get(Ram.AREA)
        paused = mem.get(Ram.PAUSED)

        # ROM latches (patched)
        # Treasure Boxes, Beaver Secret, 5-2 "speed runs", Store purchases.
        for bit, location_id in BOX_IDS.items():
            if mem.get(Ram.AP_BOX_LATCH + bit // 8) & (1 << (bit % 8)):
                report(location_id)
        odd = mem.get(Ram.AP_ODD_LATCH)
        for mask, location_id in ODD_IDS.items():
            if odd & mask:
                report(location_id)
        store = mem.get(Ram.AP_STORE_LATCH)
        for mask, location_id in STORE_IDS.items():
            if store & mask:
                report(location_id)

        # Stage Clear
        # The sentinel Area is held for the whole clear sequence, so the Level is enough.
        # The boss Location is the same moment ("Stage Clear + Boss" are two checks),
        # this is to guarantee sending the Emblem and whatever other random AP Item.
        if area == Ram.AREA_STAGE_CLEAR and stage in CLEAR_IDS:
            report(CLEAR_IDS[stage])
            report(BOSS_IDS[stage])
        goal = stage == Ram.STAGE_PETES_CASTLE and area == Ram.AREA_STAGE_CLEAR_CASTLE

        # Stage entry Costumes
        # A New Game starts with Stage/Level already set, so the first map load may falsely report the Location check.
        # The real entry always comes from the World Map into Stage transition, so it only counts once the map was seen.
        # 3-1 sends the Location instead of the vanilla 3-2 so there's two guaranteed checks before the Mini-boss.
        if area in (Ram.AREA_TITLE, Ram.AREA_INTRO):
            self.map_seen = False
        elif area == Ram.AREA_MAP:
            self.map_seen = True
        entry = COSTUME_ENTRY_IDS.get((stage, level, area))
        if entry is not None and self.map_seen:
            report(entry)

        # Mini-bosses and Rematches: falling edge of $1D8D bit 0, unless Mickey died or quit during the battle.
        # The (Stage, Level) is the one seen DURING the battle, so a slow poll cannot read the next Level.
        boss_bit = mem.get(Ram.BOSS_FLAG) & 1
        if boss_bit:
            if self.prev_boss_bit != 1:
                # A new battle starts (or the first poll finds one running). The quit counter baseline is taken ONLY
                # here: a quit bumps the counter a few frames before the map load clears the bit, so a poll in that
                # window must not refresh the baseline.
                self.battle_quit_count = mem.get(Ram.AP_QUIT_COUNT)
            if self.prev_boss_bit == 0:
                self.died_in_battle = False                        # a new battle starts
            if mem.get(Ram.HEALTH) == 0:
                self.died_in_battle = True
            self.battle_context = (stage, level)
        elif self.prev_boss_bit == 1 and self.battle_context is not None:
            # Dying also clears the bit, and so does pausing and quitting. A poll can miss the frame where the health read 0
            # while the bit was still set, so the health at the edge poll counts too (the refill comes much later).
            quit_now = mem.get(Ram.AP_QUIT_COUNT) != self.battle_quit_count
            won = (not self.died_in_battle and not quit_now and mem.get(Ram.HEALTH) != 0
                   and not (self.prev_paused or paused))
            location_id = MINI_BOSS_IDS.get(self.battle_context) or REMATCH_IDS.get(self.battle_context)
            if won and location_id is not None:
                report(location_id)
        self.prev_boss_bit, self.prev_paused = boss_bit, paused
        return goal

    # ---- Upgrade invariant ----
    # The effect flags follow the item history only. The Store no longer reads them from the Store latches, so there is nothing Store-specific left here.
    def upgrade_invariant(self, mem: Memory, items: List[int]) -> None:
        progressive = progressive_flags(items, 2)
        for flag, item_id in UPGRADE_ITEM.items():
            self.set_upgrade(mem, flag, 1 if item_id in items or flag in progressive else 0)

    @staticmethod
    def set_upgrade(mem: Memory, flag: int, value: int) -> None:
        if mem.get(flag) != value:
            mem.set(flag, value)
            mem.bump(Ram.HUD_METERS) # the meter color UI refresh

    # ---- invariants ----
    @staticmethod
    def mirror_to_ap_ram(mem: Memory, items: List[int], known: Set[int]) -> None:
        fragments = 0
        for item_id in set(items):
            effect = ITEM_EFFECT.get(item_id)
            if effect and effect[0] == "map_fragment":
                fragments |= 1 << effect[1]
        mem.set(Ram.AP_FRAGMENTS, fragments)
        mem.set(Ram.AP_EMBLEMS, min(255, items.count(EMBLEM_ID)))
        # Checked Store Locations, so the Store shows them Sold Out even after a New Game or an older savestate. Only
        # the client writes this byte; the ROM writes its own purchase latch ($7FEE17), so neither overwrites the other.
        mem.set(Ram.AP_STORE_CHECKED, sum(mask for mask, location_id in STORE_IDS.items() if location_id in known))

    def levels_played(self, mem: Memory) -> Optional[int]:
        # RAM | server back into RAM (restores them after a New Game); returns the new total when the server lacks bits.
        if self.levels_saved is None:
            return None                                            # wait for the server's copy
        ram = 0
        for i in range(Ram.AP_LEVELS_PLAYED_SIZE):
            ram |= mem.get(Ram.AP_LEVELS_PLAYED + i) << (8 * i)
        merged = ram | self.levels_saved
        if merged != ram:
            for i in range(Ram.AP_LEVELS_PLAYED_SIZE):
                mem.set(Ram.AP_LEVELS_PLAYED + i, (merged >> (8 * i)) & 0xFF)
        if merged != self.levels_saved:
            self.levels_saved = merged
            return merged
        return None

    @staticmethod
    def tracker_counts(mem: Memory, items: List[int], known: Set[int]) -> None:
        # The in-game Tracker's numbers for the current Stage, every poll (paused too), from the server's checks.
        block = TrackerData.tracker_bytes(mem.get(Ram.STAGE_INDEX), known, items.count(EMBLEM_ID))
        for offset, value in enumerate(block):
            mem.set(Ram.AP_TRACKER + offset, value)

    def max_health_invariant(self, mem: Memory, items: List[int]) -> None:
        # Purchasing a Store Big Heart doesn't grant the health increase.
        true_max = self.true_max_health(items)
        if mem.get(Ram.MAX_HEALTH) != true_max or mem.get(Ram.HEALTH) > true_max:
            mem.set(Ram.MAX_HEALTH, true_max)
            mem.set(Ram.HEALTH, min(mem.get(Ram.HEALTH), true_max))
            mem.bump(Ram.HUD_HEALTH)

    def costume_invariant(self, mem: Memory, items: List[int]) -> None:
        # Game is patched to be able to receive Costumes in any order.
        # The vanilla game grant depends on owning the previous Costume for whatever reason, so it's always locked to W -> F -> M.
        owned_flags = {ITEM_EFFECT[i][1] for i in set(items) if ITEM_EFFECT.get(i, ("",))[0] == "costume"}
        owned_flags |= progressive_flags(items, 1)
        for flag in owned_flags:
            mem.set(flag, 1)
        for flag in COSTUME_FLAGS:
            if mem.get(flag) and flag not in owned_flags and flag not in self.warned_costumes:
                self.warned_costumes.add(flag)
                self.messages.append(f"Costume flag ${flag:06X} is set without the Archipelago item (left as it is).") # Player cheated or bug.

    # ---- the dispatcher: one-shot effects driven by the received-item index ----
    def dispatch(self, mem: Memory, items: List[int]) -> int:
        index = mem.get16(Ram.AP_ITEM_INDEX)
        applied = 0
        fresh: Set[str] = set()    
        while index < len(items) and applied < MAX_ITEMS_PER_POLL:
            effect = ITEM_EFFECT.get(items[index])
            self.apply_one_shot(mem, items, effect)
            if self.jingle_from is not None and index >= self.jingle_from:
                kind = effect[0] if effect else ""
                if items[index] in FILLER_IDS:
                    kind = ""                                  # Filler: message only, no jingle
                if kind == "progressive":                      # the first copy is the Costume, the next its Upgrade
                    kind = "costume" if items[:index + 1].count(items[index]) == 1 else "upgrade"
                if kind:
                    fresh.add(kind)
                self.notice(self.describe(index) if self.describe else None)
            index += 1
            applied += 1
        if applied:
            mem.set16(Ram.AP_ITEM_INDEX, index)
        if fresh:
            # One jingle per poll. jingle_from only moves forward, so a replay of these Items stays silent.
            self.jingle_from = index
            mem.bump(Ram.AP_JINGLE_COSTUME_REQ if "costume" in fresh else Ram.AP_JINGLE_ITEM_REQ)
        return applied

    # ---- in-game messages ----
    def notice(self, message: Optional[Messages.Message]) -> None:
        if message is not None and Messages.allowed(message, self.item_messages):
            self.notices.push(message)

    def show_notice(self, mem: Memory) -> None:
        # The next message, when the ROM is idle and the screen is a Level, Store or Secret. Not on the World Map: its
        # text rows show the Level Select; messages wait for the next Level.
        area = mem.get(Ram.AREA)
        if area > 0x30 or area == 0x25 or area == Ram.AREA_MAP:
            return
        if mem.get(Ram.AP_MSG_PHASE) or mem.get(Ram.AP_MSG_REQ) != mem.get(Ram.AP_MSG_SHOWN):
            return
        while True:
            message = self.notices.next()
            if message is None:
                return
            if Messages.allowed(message, self.item_messages):    # the mode may have changed since it was queued
                break
        for offset, tile in enumerate(Messages.line_tiles(message.line1)):
            mem.set(Ram.AP_MSG_LINE1 + offset, tile)
        for offset, tile in enumerate(Messages.line_tiles(message.line2)):
            mem.set(Ram.AP_MSG_LINE2 + offset, tile)
        mem.set(Ram.AP_MSG_COLOR, message.attr)
        mem.bump(Ram.AP_MSG_REQ)                                   # the highest address: written after the text

    def apply_one_shot(self, mem: Memory, items: List[int], effect: Optional[Tuple]) -> None:
        if not effect:
            return
        kind = effect[0]
        if kind == "coins":
            total = mem.get(Ram.COINS_HUNDREDS) * 100 + mem.get(Ram.COINS_TENS) * 10 + mem.get(Ram.COINS_ONES)
            total = min(total + effect[1], Ram.MAX_COINS)            # clamp confirmed at $02FD1D
            mem.set(Ram.COINS_HUNDREDS, total // 100)
            mem.set(Ram.COINS_TENS, total % 100 // 10)
            mem.set(Ram.COINS_ONES, total % 10)
            mem.bump(Ram.HUD_COINS)
        elif kind == "refill":                                       # ("refill", meter address, amount)
            mem.set(effect[1], min(mem.get(effect[1]) + effect[2], Ram.METER_FULL))
            mem.bump(Ram.HUD_METERS)
        elif kind == "heal":                                         # Small Heart
            mem.set(Ram.HEALTH, min(mem.get(Ram.HEALTH) + effect[1], mem.get(Ram.MAX_HEALTH)))
            mem.bump(Ram.HUD_HEALTH)
        elif kind == "life":                                         # Mickey Doll
            mem.set(Ram.LIVES, min(mem.get(Ram.LIVES) + 1, Ram.MAX_LIVES_DISPLAY))
            mem.bump(Ram.HUD_LIVES)
        elif kind == "big_heart":
            # The Max Health part is the invariant's job; the item also heals fully. $02BD stays untouched.
            true_max = self.true_max_health(items)
            mem.set(Ram.MAX_HEALTH, true_max)
            mem.set(Ram.HEALTH, true_max)
            mem.bump(Ram.HUD_HEALTH)
        # costume / progressive / map_fragment / emblem / upgrade: stateless, handled by the invariants


# ---- SNI glue ---------------------------------------------------------------------------------------------------
def default_item_messages() -> str:
    # host.yaml: magical_quest_options.item_messages (all / received / off), "all" if missing or unreadable.
    try:
        from settings import get_settings
        value = str(get_settings().magical_quest_options.item_messages).strip().lower()
    except Exception:
        value = "all"
    return value if value in Messages.MODES else "all"


def cmd_item_messages(self, mode: str = "") -> bool:
    """In-game item messages: all (received, found, sent), received (no sent) or off. No value: show the setting."""
    handler = getattr(self.ctx, "client_handler", None)
    if not isinstance(handler, MagicalQuestSNIClient):
        self.output("Magical Quest is not running.")
        return False
    mode = mode.strip().lower()
    if mode:
        if mode not in Messages.MODES:
            self.output(f"Use one of: {', '.join(Messages.MODES)}.")
            return False
        handler.item_messages = mode
    self.output(f"Item messages: {handler.messages_mode()} (this session; the default is in host.yaml).")
    return True


def levels_key(ctx) -> str:
    # The server's data storage key for this slot's Levels played (Level Select).
    return f"magical_quest_levels_{getattr(ctx, 'team', 0)}_{ctx.slot}"


class MagicalQuestSNIClient(SNIClient):
    game = GAME_NAME
    patch_suffix = ".apmq"

    def __init__(self) -> None:
        self.tracker = Tracker(3)
        self.items_synced = False
        self.slot_data: Optional[dict] = None
        self.slot_data_checked = False
        self.item_messages: Optional[str] = None    # read from host.yaml on the first poll (Messages.MODES)
        self.levels_requested = False               # Get + SetNotify sent for the Levels played key

    async def validate_rom(self, ctx) -> bool:
        from SNIClient import snes_read

        signature = await snes_read(ctx, Ram.ROM_START + RomData.HEADER_TITLE_OFFSET, len(RomData.CONFIG_SIGNATURE))
        if signature is None or signature != RomData.CONFIG_SIGNATURE:
            return False
        identity = await snes_read(ctx, Ram.ROM_START + RomData.IDENTITY_BASE, IDENTITY_LENGTH)
        if identity is None or not any(identity):
            return False

        ctx.game = self.game
        ctx.items_handling = 0b111 # remote items: the server sends everything, the dispatcher applies it
        ctx.allow_collect = True
        processor = getattr(ctx, "command_processor", None)
        if processor is not None and "item_messages" not in processor.commands:
            processor.commands["item_messages"] = cmd_item_messages

        if ctx.rom != identity:
            health = await snes_read(ctx, Ram.ROM_START + RomData.MAX_HEALTH_TABLE_OFFSET, 1)
            self.tracker = Tracker(health[0] if health else 3)
            self.levels_requested = False
            self.items_synced = False
            self.slot_data_checked = False
        ctx.rom = identity
        return True

    def on_package(self, ctx, cmd: str, args: dict) -> None:
        super().on_package(ctx, cmd, args)
        if cmd == "Connected":
            self.slot_data = args.get("slot_data")
            self.slot_data_checked = False
            self.items_synced = False
            self.levels_requested = False
            self.tracker.levels_saved = None
            self.tracker.reset()
        elif cmd == "ReceivedItems":
            self.items_synced = True
        elif cmd == "Retrieved":
            keys = args.get("keys", {})
            if levels_key(ctx) in keys:
                self.saved_levels(keys[levels_key(ctx)])
        elif cmd == "SetReply" and args.get("key") == levels_key(ctx):
            self.saved_levels(args.get("value"))
        elif cmd == "PrintJSON" and args.get("type") == "ItemSend" and ctx.slot is not None:
            self.tracker.item_messages = self.messages_mode()
            self.tracker.notice(self.describe_sent(ctx, args))

    def saved_levels(self, value) -> None:
        # The server's value (None when the key was never set) joins what is already known: bits are only added.
        self.tracker.levels_saved = (self.tracker.levels_saved or 0) | (value if isinstance(value, int) else 0)

    def messages_mode(self) -> str:
        if self.item_messages is None:
            self.item_messages = default_item_messages()
        return self.item_messages

    @staticmethod
    def describe_sent(ctx, args: dict) -> Optional[Messages.Message]:
        # An Item this slot found for another slot (own Items arrive as received Items instead).
        item, receiving = args.get("item"), args.get("receiving")
        if item is None or item.player != ctx.slot or receiving == ctx.slot:
            return None
        name = ctx.item_names.lookup_in_slot(item.item, receiving)
        return Messages.sent(name, ctx.player_names.get(receiving, f"Player {receiving}"), item.flags)

    @staticmethod
    def describe_received(ctx, index: int) -> Optional[Messages.Message]:
        if index >= len(ctx.items_received):
            return None
        network_item = ctx.items_received[index]
        name = ctx.item_names.lookup_in_game(network_item.item)
        if network_item.player == ctx.slot:
            return Messages.found(name, network_item.flags)
        sender = ctx.player_names.get(network_item.player, "Archipelago")
        return Messages.received(name, sender, network_item.flags)

    def check_slot_data(self) -> None:
        # The ROM is the truth; the server's slot data is only compared, so a wrong patch or version is visible.
        data = self.slot_data or {}
        if "world_version" in data and data["world_version"] != WORLD_VERSION:
            snes_logger.warning(f"Magical Quest: the seed was generated with world version {data['world_version']}, "
                                f"this client is {WORLD_VERSION}.")
        wanted = data.get("starting_max_health")
        if wanted is not None and wanted != self.tracker.starting_max_health:
            snes_logger.warning(f"Magical Quest: the ROM starts with {self.tracker.starting_max_health} hearts but the "
                                f"seed says {wanted}: wrong patch?")
        self.slot_data_checked = True

    async def game_watcher(self, ctx) -> None:
        from SNIClient import snes_buffered_write, snes_flush_writes, snes_read

        # Wait for the item history: acting before it arrives would "repair" the invariants to an empty inventory.
        if ctx.server is None or ctx.slot is None or not self.items_synced:
            return
        block = await snes_read(ctx, Ram.wram(BLOCK_BASE), BLOCK_LENGTH)
        boss = await snes_read(ctx, Ram.wram(Ram.BOSS_FLAG), 1)
        ap_block = await snes_read(ctx, Ram.wram(Ram.AP_BLOCK), Ram.AP_BLOCK_SIZE)
        if block is None or boss is None or ap_block is None:
            return
        if not self.slot_data_checked:
            self.check_slot_data()
        if not self.levels_requested:
            self.levels_requested = True
            await ctx.send_msgs([{"cmd": "Get", "keys": [levels_key(ctx)]},
                                 {"cmd": "SetNotify", "keys": [levels_key(ctx)]}])

        self.tracker.store_hints = bool((self.slot_data or {}).get("store_hints", True))
        self.tracker.item_messages = self.messages_mode()
        self.tracker.describe = lambda index: self.describe_received(ctx, index)
        memory = Memory(block, boss[0], ap_block)
        items = [network_item.item for network_item in ctx.items_received]
        known = set(ctx.locations_checked) | set(ctx.checked_locations)
        result = self.tracker.tick(memory, items, known)

        for address, data in memory.writes():
            snes_buffered_write(ctx, address, data)
        await snes_flush_writes(ctx)

        for message in self.tracker.messages:
            snes_logger.warning(message)
        self.tracker.messages.clear()

        for location_id in result.locations:
            ctx.locations_checked.add(location_id)
            # debug only: the server already prints "X sent Y to Z (Location)" for every check.
            snes_logger.debug(f"New Check: {ctx.location_names.lookup_in_game(location_id)} "
                             f"({len(ctx.locations_checked)}/{len(ctx.missing_locations) + len(ctx.checked_locations)})")
        if result.locations:
            await ctx.send_msgs([{"cmd": "LocationChecks", "locations": result.locations}])
        if result.levels is not None:
            await ctx.send_msgs([{"cmd": "Set", "key": levels_key(ctx), "default": 0, "want_reply": False,
                                  "operations": [{"operation": "or", "value": result.levels}]}])
        if result.scout:
            # create_as_hint 2: the server makes a hint only if it is new, and it shows for everyone (any game's item)
            await ctx.send_msgs([{"cmd": "LocationScouts", "locations": list(result.scout), "create_as_hint": 2}])

        if result.goal and not ctx.finished_game:
            snes_logger.info(GOAL_TEXT)
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL},
                                 {"cmd": "Say", "text": GOAL_TEXT}]) # the Say shows the flavor text in the server log
            ctx.finished_game = True










            