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


# ---- Custom AP RAM block: 32 bytes at $7FEE00, zeroed at every New Game by a ROM patch ----------
AP_BLOCK = 0x7FEE00
AP_BLOCK_SIZE = 32

AP_FRAGMENTS = 0x7FEE00        # bit n = Map Fragment for Stage Index n (written by the client)
AP_GOAL = 0x7FEE01             # main bosses defeated (reserved; not in use yet)
AP_ITEM_INDEX = 0x7FEE02       # received-item index, 16 bits little endian ($7FEE02-$7FEE03)
# $7FEE04-$7FEE0C belong to the ROM patches; the client never touches them.
AP_EMBLEMS = 0x7FEE0D          # Pete's Emblem count, written by the client (The patched ROM reads it)
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
# $7FEE16-$7FEE1F free

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
WIZARD_UPGRADE = 0x7E02B5      # also the Store Sold-Out flag (needs to be temporarily set to 0 if visiting a Store while owning the AP Item without having checked the AP Location)
FIREFIGHTER_UPGRADE = 0x7E02B6 # also the Store Sold-Out flag (see above)
MAGIC = 0x7E02B7
WATER = 0x7E02B9
BIG_HEART_LOCK = 0x7E02BD      # Level-scoped lock; the store Big Heart Locations key off its 0 -> 1 edge. The vanilla game always sets this to 1 when obtaining a Big Heart.
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
AREA_NO_WRITE = (0x34, 0x39, 0x10, 0x24, 0x41)

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