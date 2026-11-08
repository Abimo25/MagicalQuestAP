# =========================
# = In-game Tracker data =
# =========================
# Pure logic for the in-game Tracker: the Results Screen and the pause view. The client writes the
# current Stage's counts into AP RAM every poll; the ROM only formats them. The counts come from the server's checked
# Locations, so co-op and collect are included.
#
# AP RAM block (Ram.AP_TRACKER, 25 bytes):
#   +0        Stage Index + 1 the counts are for (0 = nothing written yet)
#   +1..+18   9 categories x (checked, total), in CATEGORIES order; total 0 = the Stage has none
#   +19..+24  global: checks (checked, total), Pete's Emblems (received, 5), Upgrades (checked, 2)

from typing import Dict, Iterable, List, Set, Tuple

from .data import locations_data as data
from .data.items_data import STARTING_ID

# (label shown in game, location kind)
CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("TREASURE BOXES", data.K_BOX),
    ("STAGE CLEAR", data.K_CLEAR),
    ("BOSS", data.K_BOSS),
    ("MINI-BOSS", data.K_MINI),
    ("REMATCHES", data.K_REMATCH),
    ("SECRET", data.K_BEAVER),
    ("STORE", data.K_STORE),
    ("COSTUME", data.K_COSTUME),
    ("SPEED RUNS", data.K_SPEED),
)
STAGE_INDEX = {"Treetops": 0, "Dark Forest": 1, "Fire Grotto": 2, "Pete's Peak": 3, "Snowy Valley": 4,
               "Pete's Castle": 6}
EMBLEMS_TOTAL = 5
BLOCK_SIZE = 1 + 2 * len(CATEGORIES) + 6


def _location_id(loc) -> int:
    return STARTING_ID + loc.id_offset


# Stage Index -> category position -> Location IDs. The shared Upgrades (stage None) are not in any Stage.
STAGE_LOCATIONS: Dict[int, List[List[int]]] = {index: [[] for _ in CATEGORIES] for index in STAGE_INDEX.values()}
for _loc in data.LOCATIONS:
    if _loc.stage is None:
        continue
    _position = [kind for _, kind in CATEGORIES].index(_loc.kind)
    STAGE_LOCATIONS[STAGE_INDEX[_loc.stage]][_position].append(_location_id(_loc))

ALL_LOCATIONS: Set[int] = {_location_id(loc) for loc in data.LOCATIONS}
UPGRADE_LOCATIONS: Set[int] = {_location_id(loc) for loc in data.LOCATIONS if loc.stage is None}


def tracker_bytes(stage_index: int, checked: Iterable[int], emblems: int) -> bytes:
    """The block the client writes for the current Stage. An unknown Stage Index writes all zeros."""
    done = set(checked)
    out = bytearray(BLOCK_SIZE)
    categories = STAGE_LOCATIONS.get(stage_index)
    if categories is None:
        return bytes(out)
    out[0] = stage_index + 1
    for position, ids in enumerate(categories):
        out[1 + 2 * position] = sum(1 for i in ids if i in done)
        out[2 + 2 * position] = len(ids)
    base = 1 + 2 * len(CATEGORIES)
    out[base:base + 6] = bytes([len(done & ALL_LOCATIONS), len(ALL_LOCATIONS),
                                min(emblems, 255), EMBLEMS_TOTAL,
                                len(done & UPGRADE_LOCATIONS), len(UPGRADE_LOCATIONS)])
    return bytes(out)

