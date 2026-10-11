# ==================
# = Locations Data =
# ==================
# Final ID = STARTING_ID + id_offset (items.py shares STARTING_ID). Offsets are PERMANENT.
# Treasure Boxes use their box number 0-36, which is also the bit number in the ROM latch (AP RAM $7FEE10-$7FEE14, the
# order is arbitrary from play testing). Everything else starts at 100.
# 
# "rule" is the Location's OWN requirement as the survey states it (expression syntax in gates_data.py); the Level
# before it is the rule on the connection into "region".
# 
# "detect" says how the client sees the Location:
# - ("box", n)               bit n of the Treasure Box latch
# - ("odd", mask)            bit mask of AP RAM $7FEE15: The Beaver Secret, Snowy Valley's unique "speed run" Locations
# - ("stage_clear", stage)   Area becomes $34 in that Stage Index
# - ("boss", stage)          falling edge of $1D8D bit 0 in the Stage's boss Level
# - ("mini_boss", stage)     same, in the mini-boss Level (Stage, Level) of MINI_BOSS_LEVELS
# - ("rematch", stage, lvl)  same, in Pete's Castle Levels 6-8 (REMATCH_LEVELS)
# - ("costume_entry", stage) arriving at the Stage's first Level (COSTUME_ENTRY_LEVELS)
# - ("store_heart", area)    $02BD 0 -> 1 inside that Store Area
# - ("upgrade", wram)        the Upgrade flag ($02B5 / $02B6) goes 0 -> 1 inside a Store

from typing import NamedTuple, Optional, Tuple

from ..names import item_name as I
from ..names import location_name as L
from ..names import region_name as R
from .items_data import STARTING_ID

K_BOX, K_CLEAR, K_BOSS, K_MINI, K_REMATCH, K_COSTUME, K_STORE, K_BEAVER, K_SPEED = (
    "Treasure Boxes", "Stage Clears", "Stage Bosses", "Mini-bosses", "Rematches", "Costumes", "Store", "Beaver", "Speed Runs")
G_SECRETS = "Secrets"
G_GENERAL_STORE = "General Store"
STAGE_GROUP = {          # Stage region -> Location group of the same name
    R.treetops: "Treetops", R.dark_forest: "Dark Forest", R.fire_grotto: "Fire Grotto",
    R.petes_peak: "Pete's Peak", R.snowy_valley: "Snowy Valley", R.petes_castle: "Pete's Castle",
}


class LocationData(NamedTuple):
    name: str
    id_offset: int
    region: str
    rule: str                       # own requirement, "" = none
    kind: str                       # one of the K_* values
    stage: Optional[str]            # Stage region this Location belongs to for the Stage group; None = General Store
    detect: Tuple
    secret: bool = False            # inside a Secret (also in the Secrets group)
    hard_only: bool = False         # route only exists on Hard: excluded while hard_only_box_filler is on (Treetops 1-2 Box B)


def _box(n, name, region, stage, rule="", secret=False, hard_only=False):
    return LocationData(name, n, region, rule, K_BOX, stage, ("box", n), secret, hard_only)


T, D, F, P, S, C = R.treetops, R.dark_forest, R.fire_grotto, R.petes_peak, R.snowy_valley, R.petes_castle

LOCATIONS = [
    # ---- Treasure Boxes, in latch order (names/location_name.py) ---------------------------------------
    _box(0, L.treetops_1_1_box_a, R.treetops_1_1, T),                      # Normally, it only spawns after talking to the wizard. ROM is patched to always skip this cutscene.
    _box(1, L.treetops_1_1_box_b_secret, R.treetops_1_1, T, secret=True),
    _box(2, L.treetops_1_1_box_c, R.treetops_1_1, T),
    _box(3, L.treetops_1_1_box_d, R.treetops_1_1, T),
    _box(4, L.treetops_1_1_box_e, R.treetops_1_1, T),
    _box(5, L.treetops_1_2_box_a, R.treetops_1_2, T),
    _box(6, L.treetops_1_2_box_b, R.treetops_1_2, T, hard_only=True),      # An enemy spawns only on Hard, and it allows the player to reach it.
    _box(7, L.treetops_1_2_box_c, R.treetops_1_2, T),
    _box(8, L.treetops_1_3_box_a, R.treetops_1_3, T),
    _box(9, L.treetops_1_3_box_b, R.treetops_1_3, T),
    _box(10, L.dark_forest_2_1_box_a, R.dark_forest_2_1, D),
    _box(11, L.dark_forest_2_1_box_b_secret, R.dark_forest_2_1, D, secret=True),
    _box(12, L.dark_forest_2_1_box_c, R.dark_forest_2_1, D),
    _box(13, L.fire_grotto_3_1_box_a, R.fire_grotto_3_1, F),
    _box(14, L.fire_grotto_3_2_box_a_secret, R.fire_grotto_3_2, F, "F | M", secret=True),
    _box(15, L.fire_grotto_3_2_box_b, R.fire_grotto_3_2, F, "F | M"),
    _box(16, L.fire_grotto_3_2_box_c, R.fire_grotto_3_2, F, "F | M"),
    _box(17, L.fire_grotto_3_2_box_d, R.fire_grotto_3_2, F, "F | (M & W)"),
    _box(18, L.fire_grotto_3_3_box_a, R.fire_grotto_3_3, F, "F"),        # Wizard can still open it through the patched Grey Blocks, but taking damage is unavoidable.
    _box(19, L.fire_grotto_3_3_box_b, R.fire_grotto_3_3, F, "W"),        # Underwater; players can grab a Gold Block from the Grey Block room and walk all the way back to open it, but taking damage is unavoidable.
    _box(20, L.fire_grotto_3_3_box_c, R.fire_grotto_3_3, F, "F | M"),
    _box(21, L.pete_s_peak_4_1_box_a, R.petes_peak_4_1, P),              # ROM is patched to spawn a Red Block the player can jump on, so it's always available.
    _box(22, L.pete_s_peak_4_1_box_b, R.petes_peak_4_1, P, "M"),
    _box(23, L.pete_s_peak_4_2_box_a, R.petes_peak_4_2, P),
    _box(24, L.pete_s_peak_4_2_box_b, R.petes_peak_4_2, P, "M"),
    _box(25, L.pete_s_peak_4_2_box_c, R.petes_peak_4_2, P, "M"),
    _box(26, L.pete_s_peak_4_2_box_d, R.petes_peak_4_2, P, "M"),
    _box(27, L.snowy_valley_5_1_box_a, R.snowy_valley_5_1, S),
    _box(28, L.snowy_valley_5_1_box_b, R.snowy_valley_5_1, S, "F"),
    _box(29, L.snowy_valley_5_1_box_c, R.snowy_valley_5_1, S),           # Players can throw an enemy to get it, so Firefighter is not needed.
    _box(30, L.pete_s_castle_6_1_box_a, R.petes_castle_6_1, C),
    _box(31, L.pete_s_castle_6_1_box_b, R.petes_castle_6_1, C),
    _box(32, L.pete_s_castle_6_1_box_c, R.petes_castle_6_1, C),
    _box(33, L.pete_s_castle_6_1_box_d, R.petes_castle_6_1, C),
    _box(34, L.pete_s_castle_6_1_box_e, R.petes_castle_6_1, C),
    _box(35, L.pete_s_castle_6_1_box_f, R.petes_castle_6_1, C, "W"),     # Underwater; players can grab a nearby Gold Block or enemy to open it, but taking damage is unavoidable.
    _box(36, L.pete_s_castle_6_3_box_a, R.petes_castle_6_3, C, "F"),

    # ---- Stage Clears (Pete's Castle's is the goal) ---------------------------------------------------
    LocationData(L.treetops_cleared, 100, R.treetops_1_4, "", K_CLEAR, T, ("stage_clear", 0)),
    LocationData(L.dark_forest_cleared, 101, R.dark_forest_2_4, "", K_CLEAR, D, ("stage_clear", 1)),
    LocationData(L.fire_grotto_cleared, 102, R.fire_grotto_3_4, "F", K_CLEAR, F, ("stage_clear", 2)),
    LocationData(L.pete_s_peak_cleared, 103, R.petes_peak_4_3, "M", K_CLEAR, P, ("stage_clear", 3)),
    LocationData(L.snowy_valley_cleared, 104, R.snowy_valley_5_3, "W | F", K_CLEAR, S, ("stage_clear", 4)),

    # ---- Stage Bosses (Emperor Pete is the goal) -------------------------------------------------------
    LocationData(L.treetops_boss, 110, R.treetops_1_4, "", K_BOSS, T, ("boss", 0)),
    LocationData(L.dark_forest_boss, 111, R.dark_forest_2_4, "", K_BOSS, D, ("boss", 1)),
    LocationData(L.fire_grotto_boss, 112, R.fire_grotto_3_4, "F", K_BOSS, F, ("boss", 2)),
    LocationData(L.pete_s_peak_boss, 113, R.petes_peak_4_3, "M", K_BOSS, P, ("boss", 3)),
    LocationData(L.snowy_valley_boss, 114, R.snowy_valley_5_3, "W | F", K_BOSS, S, ("boss", 4)),

    # ---- Mini-bosses and Rematches ---------------------------------------------------------------------
    LocationData(L.treetops_mini_boss, 120, R.treetops_1_2, "", K_MINI, T, ("mini_boss", 0)),
    LocationData(L.dark_forest_mini_boss, 121, R.dark_forest_2_2, "W", K_MINI, D, ("mini_boss", 1)),
    LocationData(L.fire_grotto_mini_boss, 122, R.fire_grotto_3_1, "", K_MINI, F, ("mini_boss", 2)),   # Patched Red Blocks so Wizard isn't needed.
    LocationData(L.treetops_mini_boss_rematch, 130, R.petes_castle_6_3, "F", K_REMATCH, C, ("rematch", 6, 6)),
    LocationData(L.dark_forest_mini_boss_rematch, 131, R.petes_castle_6_3, "F", K_REMATCH, C, ("rematch", 6, 7)),
    LocationData(L.fire_grotto_mini_boss_rematch, 132, R.petes_castle_6_3, "F", K_REMATCH, C, ("rematch", 6, 8)),

    # ---- Stage-entry Costumes (free checks) -----------------------------------------------------------
    LocationData(L.dark_forest_costume_wizard, 140, R.dark_forest_2_1, "", K_COSTUME, D, ("costume_entry", 1)),
    LocationData(L.fire_grotto_costume_firefighter, 141, R.fire_grotto_3_1, "", K_COSTUME, F, ("costume_entry", 2)), # This is actually granted in 3-2, but 3-1 was decided to give at least two checks before the Mini-boss.
    LocationData(L.pete_s_peak_costume_mountaineer, 142, R.petes_peak_4_1, "", K_COSTUME, P, ("costume_entry", 3)),

    # ---- Store purchases ------------------------------------------------------------------------------
    # The 300 Mickey Coins Item is needed for all of these, so the player isn't expected to grind for a Store Location.
    LocationData(L.dark_forest_store_big_heart, 150, R.dark_forest_store, "COINS", K_STORE, D, ("store_heart", 46)),
    LocationData(L.petes_castle_store_big_heart, 151, R.petes_castle_store, "COINS", K_STORE, C, ("store_heart", 47)),
    LocationData(L.store_magic_upgrade, 152, R.general_store, "COINS & W", K_STORE, None, ("upgrade", 0x7E02B5)),
    LocationData(L.store_water_upgrade, 153, R.general_store, "COINS & F", K_STORE, None, ("upgrade", 0x7E02B6)),

    # ---- Beaver Secret and the Snowy Valley 5-2 speed runs (ROM latch $7FEE15) -----------------------------
    LocationData(L.treetops_beaver_secret, 160, R.treetops_1_3, "", K_BEAVER, T, ("odd", 0x01), secret=True), # Not really a Secret area in the game, but the Beaver 2-up is a unique thing.
    LocationData(L.snowy_valley_5_2_under_15, 170, R.snowy_valley_5_2, "", K_SPEED, S, ("odd", 0x02)), # Just so 5-2 has something going for it.
    LocationData(L.snowy_valley_5_2_under_25, 171, R.snowy_valley_5_2, "", K_SPEED, S, ("odd", 0x04)), # Just so 5-2 has something going for it.
]

# The goal: an Event Location at Emperor Pete, gives "Victory"
EVENT_REGION = R.petes_castle_6_4
EVENT_RULE = "W" # I think Emperor Pete may be also beatable with Firefighter, but I didn't try.

LOCATION_BY_NAME = {loc.name: loc for loc in LOCATIONS}
BOX_LOCATIONS = [loc for loc in LOCATIONS if loc.kind == K_BOX]
EMBLEM_LOCATIONS = (L.treetops_boss, L.dark_forest_boss, L.fire_grotto_boss, L.pete_s_peak_boss, L.snowy_valley_boss)
HARD_ONLY_LOCATIONS = tuple(loc.name for loc in LOCATIONS if loc.hard_only)

# ---- Game Mode (Options.GameMode): what each mode precollects and locks at generation time -----------------
# Open World: these five Map Fragments are in the start inventory; only the Pete's Castle Fragment stays in the pool.
OPEN_WORLD_FRAGMENTS = (I.treetops_map_fragment, I.dark_forest_map_fragment, I.fire_grotto_map_fragment,
                        I.petes_peak_map_fragment, I.snowy_valley_map_fragment)
# Linear and Vanilla Progression: clearing a Stage (its "cleared" Location, not the boss Location, which holds an Emblem)
# unlocks the next Stage in the game's own order instead of giving a random AP Item.
LINEAR_CLEAR_UNLOCKS = {
    L.treetops_cleared: I.dark_forest_map_fragment,
    L.dark_forest_cleared: I.fire_grotto_map_fragment,
    L.fire_grotto_cleared: I.petes_peak_map_fragment,
    L.pete_s_peak_cleared: I.snowy_valley_map_fragment,
    L.snowy_valley_cleared: I.petes_castle_map_fragment,
}
# Vanilla Progression only: each Costume on the Costume Location of the Stage that gives it in the vanilla game.
VANILLA_COSTUME_UNLOCKS = {
    L.dark_forest_costume_wizard: I.wizard_costume,
    L.fire_grotto_costume_firefighter: I.firefighter_costume,
    L.pete_s_peak_costume_mountaineer: I.mountaineer_costume,
}


def location_groups():
    # AP location_name_groups: a Location may be in several (kind, Stage, Secrets, General Store).
    groups = {}
    for loc in LOCATIONS:
        names = set() if loc.kind == K_BEAVER else {loc.kind} # the Beaver Secret is only in "Secrets"
        if loc.stage is None:
            names.add(G_GENERAL_STORE) # the Upgrades belong to the General Store only
        else:
            names.add(STAGE_GROUP[loc.stage])
        if loc.secret:
            names.add(G_SECRETS)
        for group in names:
            groups.setdefault(group, set()).add(loc.name)
    return groups


