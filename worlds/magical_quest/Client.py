# ==============
# = SNI Client =
# ==============

# - STATELESS INVARIANTS (re-evaluated at every poll from the item history alone, so if the player resets, does a savestate load or a
#   reconnect, it repairs itself): Map Fragments ($7FEE00), Pete's Emblem count ($7FEE0D), Max Health, the two Upgrade
#   flags, the Costume flags.
# - ONE-SHOT EFFECTS (coins, refills, Small Heart, Mickey Doll, the Big Heart heal) are applied once, in order, driven by
#   the received-item index in AP RAM ($7FEE02-$7FEE03). The index lives in the game's RAM on purpose: a New Game
#   zeroes it and the history is replayed, a savestate load restores it together with the state it belongs to. It only
#   advances while the safety gate is open, so no item is ever lost, only delayed.
# - The AP block is ignored until the ROM has marked it valid ($7FEE1C-$7FEE1F = "MQOK"): bank $7F is not cleared at boot,
#   so before the title screen it is garbage and triggers a bunch of fake Location checks without this patch.
# - The client never writes $02BD (the vanilla game uses this as a failsafe to stop the player from grabbing multiple Big Hearts).
# - Locations are detected from the ROM latches ($7FEE10-$7FEE15) and from vanilla RAM (Area, Stage, Level, $1D8D,
#   $02BD, the Upgrade flags).

import logging
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from NetUtils import ClientStatus
from worlds.AutoSNIClient import SNIClient

from . import Ram, RomData
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
EMBLEM_ID = ITEM_ID[I.petes_emblem]
MAX_HEALTH_CAP = 10

COSTUME_FLAGS = (Ram.COSTUME_WIZARD, Ram.COSTUME_FIREFIGHTER, Ram.COSTUME_MOUNTAINEER)
UPGRADE_ITEM = {Ram.WIZARD_UPGRADE: ITEM_ID[I.magic_upgrade], Ram.FIREFIGHTER_UPGRADE: ITEM_ID[I.water_upgrade]}
# Stores that sell a Big Heart: Area -> (Stage Index, Level Index) of the Store Level.
STORE_HEART_LEVELS = {Ram.AREA_STORE_DARK_FOREST: (Ram.STAGE_DARK_FOREST, 6),
                      Ram.AREA_STORE_PETES_CASTLE: (Ram.STAGE_PETES_CASTLE, 5)}


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
STORE_HEART_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("store_heart").items()}  # Store Area -> ID
UPGRADE_IDS: Dict[int, int] = {key[0]: lid for key, lid in _index("upgrade").items()}          # flag address -> ID


def detectable_ids() -> Set[int]:
    # Every Location ID the Tracker can report (the test checks this is every Location of the world).
    ids: Set[int] = set(BOX_IDS.values()) | set(ODD_IDS.values()) | set(CLEAR_IDS.values()) | set(BOSS_IDS.values())
    ids |= set(MINI_BOSS_IDS.values()) | set(REMATCH_IDS.values()) | set(COSTUME_ENTRY_IDS.values())
    ids |= set(STORE_HEART_IDS.values()) | set(UPGRADE_IDS.values())
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
    scout: Tuple[int, ...] = ()  # Store Locations to send as hints, once each per connection (so the player can know what is actually in the Store before purchasing a Location check).


# ---- The logic ------------------------------------------------------------------------------------------------
class Tracker:
    def __init__(self, starting_max_health: int):
        self.starting_max_health = max(1, min(MAX_HEALTH_CAP, starting_max_health))
        self.store_hints = True
        self.reset()

    def reset(self) -> None:
        # Basically, forget everything seen in RAM (a new ROM, a reconnect). The edge detectors need one poll to arm again.
        self.prev_boss_bit: Optional[int] = None
        self.prev_paused = 0
        self.battle_context: Optional[Tuple[int, int]] = None      # (Stage, Level) seen during the boss battle.
        self.died_in_battle = False
        self.battle_quit_count: Optional[int] = None
        self.prev_area: Optional[int] = None
        self.map_seen = False                                      # the World Map was seen since the last title/intro.
        self.prev_big_heart_lock: Optional[int] = None
        self.upgrade_forced: Dict[int, bool] = {flag: False for flag in UPGRADE_ITEM}
        self.warned_costumes: Set[int] = set()
        self.hinted: Set[int] = set()                              # Store Locations already sent as hints.
        self.messages: List[str] = []

    # ---- derived from the item history ----
    def true_max_health(self, items: List[int]) -> int:
        return min(MAX_HEALTH_CAP, self.starting_max_health + items.count(BIG_HEART_ID))

    @staticmethod
    def safe_to_write(mem: Memory) -> bool:
        return mem.get(Ram.PAUSED) == 0 and mem.get(Ram.AREA) not in Ram.AREA_NO_WRITE

    # ---- one poll ----
    def tick(self, mem: Memory, items: List[int], known: Set[int]) -> TickResult:
        new: List[int] = []
        if bytes(mem.get(Ram.AP_MAGIC + i) for i in range(len(Ram.AP_MAGIC_VALUE))) != Ram.AP_MAGIC_VALUE:
            # The title init has not cleared the AP block yet (power-on garbage): read nothing, write nothing, and
            # forget the edge detectors so they arm again on clean data.
            self.reset()
            return TickResult(new, False)

        def report(location_id: int) -> None:
            if location_id not in known and location_id not in new:
                new.append(location_id)

        goal = self.detect_locations(mem, report)
        self.upgrade_invariant(mem, items, known, report)
        self.mirror_to_ap_ram(mem, items)
        self.max_health_invariant(mem, items)
        if self.safe_to_write(mem):
            self.costume_invariant(mem, items)
            self.dispatch(mem, items)
        return TickResult(new, goal, self.store_hint_ids(mem, known))

    def store_hint_ids(self, mem: Memory, known: Set[int]) -> Tuple[int, ...]:
        # Inside a Store: the Locations to hint. The Upgrades are the same Location in every Store; the Big Heart only
        # in its own Store (Dark Forest, Pete's Castle). Each is sent once per connection, and never when already
        # checked. The server's own 'only new' rule keeps a repeat after a reconnect from making a duplicate hint.
        area = mem.get(Ram.AREA)
        if not self.store_hints or area not in Ram.STORE_AREAS:
            return ()
        wanted = list(UPGRADE_IDS.values())
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
        # Treasure Boxes, Beaver Secret, 5-2 "speed runs".
        for bit, location_id in BOX_IDS.items():
            if mem.get(Ram.AP_BOX_LATCH + bit // 8) & (1 << (bit % 8)):
                report(location_id)
        odd = mem.get(Ram.AP_ODD_LATCH)
        for mask, location_id in ODD_IDS.items():
            if odd & mask:
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

        # Store Big Hearts
        # $02BD goes 0 -> 1 inside the Store (scopes the Level; only the purchase sets it since it's not touched otherwise)
        lock = mem.get(Ram.BIG_HEART_LOCK)
        if (area in STORE_HEART_LEVELS and (stage, level) == STORE_HEART_LEVELS[area]
                and self.prev_area == area and self.prev_big_heart_lock == 0 and lock == 1):
            report(STORE_HEART_IDS[area])
        self.prev_area, self.prev_big_heart_lock = area, lock

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

    # ---- Upgrade Store invariant (or what to do if the player got the Upgrade AP Item but hasn't checked the Upgrade AP Location) ----
    def upgrade_invariant(self, mem: Memory, items: List[int], known: Set[int], report) -> None:
        inside_store = mem.get(Ram.AREA) in Ram.STORE_AREAS
        for flag, item_id in UPGRADE_ITEM.items():
            owned = item_id in items
            location_id = UPGRADE_IDS[flag]
            current = mem.get(flag)
            if location_id in known or not inside_store:
                self.set_upgrade(mem, flag, 1 if owned else 0)
                if not inside_store:
                    self.upgrade_forced[flag] = False
            elif owned:
                # Owned, unchecked: the flag is forced to 0 so the Store sells it; the own forced 0 -> 1 is the purchase.
                # The player has the Upgrade temporarily disabled inside a Store if they haven't checked the Location.
                if self.upgrade_forced[flag] and current == 1:
                    report(location_id)
                else:
                    self.set_upgrade(mem, flag, 0)
                    self.upgrade_forced[flag] = True
            elif current == 1:
                # Not owned, unchecked: vanilla flipped the flag by itself, a purchase. Report it, suppress the effect.
                report(location_id)
                self.set_upgrade(mem, flag, 0)

    @staticmethod
    def set_upgrade(mem: Memory, flag: int, value: int) -> None:
        if mem.get(flag) != value:
            mem.set(flag, value)
            mem.bump(Ram.HUD_METERS) # the meter color UI refresh

    # ---- invariants ----
    @staticmethod
    def mirror_to_ap_ram(mem: Memory, items: List[int]) -> None:
        fragments = 0
        for item_id in set(items):
            effect = ITEM_EFFECT.get(item_id)
            if effect and effect[0] == "map_fragment":
                fragments |= 1 << effect[1]
        mem.set(Ram.AP_FRAGMENTS, fragments)
        mem.set(Ram.AP_EMBLEMS, min(255, items.count(EMBLEM_ID)))

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
        while index < len(items) and applied < MAX_ITEMS_PER_POLL:
            self.apply_one_shot(mem, items, ITEM_EFFECT.get(items[index]))
            index += 1
            applied += 1
        if applied:
            mem.set16(Ram.AP_ITEM_INDEX, index)
        return applied

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
        # costume / map_fragment / emblem / upgrade: stateless, handled by the invariants


# ---- SNI glue ---------------------------------------------------------------------------------------------------
class MagicalQuestSNIClient(SNIClient):
    game = GAME_NAME
    patch_suffix = ".apmq"

    def __init__(self) -> None:
        self.tracker = Tracker(3)
        self.items_synced = False
        self.slot_data: Optional[dict] = None
        self.slot_data_checked = False

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

        if ctx.rom != identity:
            health = await snes_read(ctx, Ram.ROM_START + RomData.MAX_HEALTH_TABLE_OFFSET, 1)
            self.tracker = Tracker(health[0] if health else 3)
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
            self.tracker.reset()
        elif cmd == "ReceivedItems":
            self.items_synced = True

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

        self.tracker.store_hints = bool((self.slot_data or {}).get("store_hints", True))
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
        if result.scout:
            # create_as_hint 2: the server makes a hint only if it is new, and it shows for everyone (any game's item)
            await ctx.send_msgs([{"cmd": "LocationScouts", "locations": list(result.scout), "create_as_hint": 2}])

        if result.goal and not ctx.finished_game:
            snes_logger.info(GOAL_TEXT)
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL},
                                 {"cmd": "Say", "text": GOAL_TEXT}]) # the Say shows the flavor text in the server log
            ctx.finished_game = True