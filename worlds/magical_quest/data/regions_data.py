# ================
# = Regions Data =
# ================
from ..names import region_name as R
from .gates_data import STAGE_LEVELS, STORE_DOORS

# Every Level region -> its Stage region
LEVEL_STAGE = {level: stage for stage, levels in STAGE_LEVELS.items() for level in levels}
# Every Store region -> the Stage it belongs to (the Store of that Stage), the General Store belongs to none
STORE_STAGE = {
    R.treetops_store: R.treetops,
    R.dark_forest_store: R.dark_forest,
    R.fire_grotto_store: R.fire_grotto,
    R.petes_peak_store: R.petes_peak,
    R.petes_castle_store: R.petes_castle,
}

STAGES = list(STAGE_LEVELS) # in "Stage Index" order, taken from the game's RAM (0, 1, 2, 3, 4, 6). Pete's Castle is 6 for some reason.
STORES = [store for _, store, _ in STORE_DOORS]
ALL_REGIONS = [R.menu, *STAGES, *LEVEL_STAGE, *STORES, R.general_store]
