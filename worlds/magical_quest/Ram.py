# =================
# = RAM addresses =
# =================
# Notation: every address is the CPU address of a WRAM byte ($7E0000-$7FFFFF). "wram()" converts it to the address SNI wants.

# ---- SNI address spaces (SNIClient convention) ----------------------------------------------------
WRAM_START = 0xF50000
SRAM_START = 0xE00000
ROM_START = 0x000000


def wram(cpu_address: int) -> int:
    # CPU address $7E0000-$7FFFFF (or the $0000-$1FFF mirror of bank $7E) to the SNI WRAM address.
    return WRAM_START + (cpu_address & 0x1FFFF)


# ---- Custom AP RAM block: $7FEE00-$7FEEFF, zeroed at every New Game by a ROM patch (NewGame 1.5.0) ----------
AP_BLOCK = 0x7FEE00
AP_BLOCK_SIZE = 0xE7           # what the client reads each poll ($7FEE00-$7FEEE6)

AP_FRAGMENTS = 0x7FEE00        # bit n = Map Fragment for Stage Index n (written by the client)
AP_GOAL = 0x7FEE01             # main bosses defeated (reserved; not in use yet)
AP_ITEM_INDEX = 0x7FEE02       # received-item index, 16 bits little endian ($7FEE02-$7FEE03)
# $7FEE04-$7FEE0C belong to the ROM patches; the client never touches them.
AP_EMBLEMS = 0x7FEE0D          # Pete's Emblem count, written by the client (The patched ROM reads it)
AP_JINGLE_ITEM_DONE = 0x7FEE0E     # general jingle played (ROM only; the client never writes it)
AP_JINGLE_COSTUME_DONE = 0x7FEE0F  # Costume jingle played (ROM only)
AP_MAGIC = 0x7FEE1C            # $7FEE1C-$7FEE1F = "MQOK" once the ROM has cleared the block at the title
AP_MAGIC_VALUE = b"MQOK"
# Bank $7F is not cleared at boot: until the marker is there the whole AP block is power-on garbage and is ignored.

# ---- Location latches, written by the ROM (the client only reads them) -------------------------------
# Treasure Boxes, the Beaver Secret and the 5-2 speed runs cannot be detected by polling vanilla RAM, so the ROM latches them.
AP_QUIT_COUNT = 0x7FEE16 # Pause and Quit counter: a change during a Mini-boss battle = quit, not a win. 
AP_BOX_LATCH = 0x7FEE10 # 5 bytes ($7FEE10-$7FEE14), bit n = Treasure Box number n opened (order of names/location_name.py)
AP_BOX_LATCH_SIZE = 5
AP_ODD_LATCH = 0x7FEE15 # bit 0 = Beaver Secret, bit 1 = Snowy Valley speed run 15, bit 2 = Snowy Valley speed run 25.
ODD_BEAVER_BIT = 0x01
ODD_SPEEDRUN_15_BIT = 0x02
ODD_SPEEDRUN_25_BIT = 0x04
AP_STORE_LATCH = 0x7FEE17 # Store purchases: bit 0 Dark Forest Big Heart, bit 1 Pete's Castle Big Heart,
                          # bits 4-6 Treetops, Fire Grotto, Pete's Peak Big Heart (after 0.2.0),
                          # bit 2 Magic Upgrade, bit 3 Water Upgrade. Written by the ROM only.
AP_STORE_CHECKED = 0x7FEE18 # Same bits, written by the client only: Store Locations already checked. The ROM shows a slot
                            # as Sold Out when its bit is set in either byte (two bytes, so the two writers never race).
AP_JINGLE_ITEM_REQ = 0x7FEE19     # general "got an item" jingle requests: the client increments it (ROM reads only)
AP_JINGLE_COSTUME_REQ = 0x7FEE1A  # Costume jingle requests: the client increments it (ROM reads only)
# $7FEE1B free

# ---- In-game messages (0.2.0) ---------------------------------------------------------------
AP_MSG_LINE1 = 0x7FEE20        # 60 tiles, $FF ends a shorter line (client)
AP_MSG_LINE2 = 0x7FEE5C        # 60 tiles (client)
AP_MSG_COLOR = 0x7FEE98        # tile attribute in a Level (client); the World Map always uses $38
AP_MSG_REQ = 0x7FEE99          # request counter (client), written last so it arrives after the text
AP_MSG_SHOWN = 0x7FEE9A        # copy of the request counter once drawn (ROM)
AP_MSG_PHASE = 0x7FEE9C        # 0 idle, 1-3 a message is up (ROM)
ATTR_PROGRESSION = 0x2C        # light blue, the "PAUSE" colour
ATTR_USEFUL = 0x20             # white-yellow
ATTR_FILLER = 0x30             # dark grey
ATTR_TRAP = 0x24               # yellow / red (traps from other games)

# ---- In-game Tracker (0.2.0): the current Stage's counts, written by the client every poll ----------
AP_TRACKER = 0x7FEEB0          # 25 bytes, layout in TrackerData.py
# Level Select: $7FEEE0 + Stage Index = Levels played (bit n = Level Index n). The ROM sets
# bits as the player plays; the client ORs them with the copy saved on the server (data storage) and writes the result
# back, so they survive an emulator restart. $7FEEE7-$7FEEEE is the ROM's own L/R and "X-Y" state (not read).
# (there was a bug that used $7FEED0, which is the Tracker's scratch: its counters showed up as Levels played. Bug was fixed)
AP_LEVELS_PLAYED = 0x7FEEE0
AP_LEVELS_PLAYED_SIZE = 7

# ---- Vanilla WRAM: where we are -----------------------------------------------------------------
DIFFICULTY = 0x7E0018          # 0 Easy, 1 Normal, 3 Hard (Not used, set by the game)
STAGE_INDEX = 0x7E02AB         # 0 Treetops .. 4 Snowy Valley, 6 Pete's Castle (5 never occurs, Pete's Castle skips to 6 for some reason)
LEVEL_INDEX = 0x7E02AC
AREA = 0x7E02AD
PAUSED = 0x7E0343              # nonzero while paused
BOSS_FLAG = 0x7E1D8D           # bit 0: boss fight active (falling edge = won), not valid for Emperor Pete
EMPEROR_PETE_FLAG = 0x7E0388   # boss marker for Emperor Pete only (the goal)
TIMER = 0x7E035D               # 3 decimal digits $035D-$035F (5-2 starts at 300)

# ---- Vanilla WRAM: player state the dispatcher writes --------------------------------------------
MAX_HEALTH = 0x7E02B0
HEALTH = 0x7E02B1
ACTIVE_COSTUME = 0x7E02B3      # 0 Normal, 1 Wizard, 2 Firefighter, 3 Mountaineer
WIZARD_UPGRADE = 0x7E02B5      # the effect flag; vanilla also used it for Sold Out, patch uses the Store latches instead
FIREFIGHTER_UPGRADE = 0x7E02B6 # (see above)
MAGIC = 0x7E02B7
WATER = 0x7E02B9
BIG_HEART_LOCK = 0x7E02BD      # Level-scoped lock, set to 1 when a Big Heart is obtained (Treasure Box drop guard). Never written by the client.
COINS_HUNDREDS = 0x7E02A8      # three decimal digits $02A8-$02AA (hundreds, tens, ones)
COINS_TENS = 0x7E02A9
COINS_ONES = 0x7E02AA
LIVES = 0x7E0372               # the display caps at 9
COSTUME_WIZARD = 0x7E02C1
COSTUME_FIREFIGHTER = 0x7E02C2
COSTUME_MOUNTAINEER = 0x7E02C3

# HUD dirty flags: increment after writing the matching value so the HUD redraws at once
HUD_HEALTH = 0x7E0378
HUD_LIVES = 0x7E0379
HUD_COINS = 0x7E037B
HUD_METERS = 0x7E037E          # Magic and Water meters

# ---- Constants -------------------------------------------------------------------------------------
STAGE_TREETOPS, STAGE_DARK_FOREST, STAGE_FIRE_GROTTO, STAGE_PETES_PEAK, STAGE_SNOWY_VALLEY = 0, 1, 2, 3, 4
STAGE_PETES_CASTLE = 6
STAGE_INDEXES = (0, 1, 2, 3, 4, 6)

MAX_COINS = 999
MAX_LIVES_DISPLAY = 9
METER_FULL = 0x20
AMMO_REFILL = 8                # Magic Lamp and Fire Hydrant

# Area values (the Area is what Stage clears and Stores are detected by)
AREA_STAGE_CLEAR = 0x34        # every Stage but Pete's Castle
AREA_STAGE_CLEAR_CASTLE = 0x39 # Pete's Castle: the goal
AREA_MAP = 0x24                # the World Map
AREA_INTRO = 0x35              # Stage intro cutscene (also what a New Game's first Stage shows before its first map)
AREA_TITLE = 0x40              # Title screen
# Intermediate Areas during which the dispatcher must not write
AREA_NO_WRITE = (0x34, 0x39, 0x10, 0x41)   # the World Map ($24) was removed: items are delivered there too
# $10 is also Snowy Valley 5-1 (Stage 4, Level 0). The transition phase only follows a Results screen, so its Level
# Index is never 0 in Stage 4; 5-1 itself is safe.
AREA_TRANSIT_OR_5_1 = 0x10
LEVEL_5_1 = (4, 0)

AREA_STORE_PETES_PEAK = 44     # Store 04
AREA_STORE_TREETOPS = 45       # Store 01
AREA_STORE_DARK_FOREST = 46    # Store 02
AREA_STORE_PETES_CASTLE = 47   # Store 05
AREA_STORE_FIRE_GROTTO = 48    # Store 03
STORE_AREAS = (44, 45, 46, 47, 48)

# Mini-boss and Rematch detection: (Stage Index, Level Index) at the falling edge of BOSS_FLAG bit 0
MINI_BOSS_LEVELS = {(0, 1): "Treetops", (1, 2): "Dark Forest", (2, 1): "Fire Grotto"}
REMATCH_LEVELS = {(6, 6): "Treetops", (6, 7): "Dark Forest", (6, 8): "Fire Grotto"}
# Stage-entry Costume Locations: (Stage Index, Level Index, Area)
COSTUME_ENTRY_LEVELS = {
    "Dark Forest": (1, 1, 4),
    "Fire Grotto": (2, 1, 8),
    "Pete's Peak": (3, 0, 12),
}
# Snowy Valley 5-2: elapsed seconds = 300 - Timer when Level Index goes 1 -> 2 in Stage Index 4 (Area not AREA_MAP)
SPEED_RUN_START_TIME = 300
SPEED_RUN_LIMITS = (16, 26) # unused since the client never reads the Timer (ROM latch instead). Checks are elapsed < 16 and < 26 (rounded to "under 15 / 25 seconds" just for display)