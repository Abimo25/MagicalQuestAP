# ==============
# = Items Data =
# ==============
# Final ID = STARTING_ID + id_offset. Offsets are PERMANENT: never renumber, never reuse; add new
# items at the end of their block. "effect" tells Client.py what receiving the item does.
from typing import NamedTuple, Optional, Tuple

from ..names import item_name as I
from ..Ram import (STAGE_TREETOPS, STAGE_DARK_FOREST, STAGE_FIRE_GROTTO, STAGE_PETES_PEAK, STAGE_SNOWY_VALLEY,
                   STAGE_PETES_CASTLE)

STARTING_ID = 0x4D510000            # "MQ" in the high half; shared by items and locations (separate namespaces)

PROGRESSION, USEFUL, FILLER = "progression", "useful", "filler"

G_COSTUMES = "Costumes"
G_MAP_FRAGMENTS = "Map Fragments"
G_COINS = "Mickey Coins"
G_UPGRADES = "Upgrades"
G_REFILLS = "Refills"


class ItemData(NamedTuple):
    name: str
    id_offset: int
    classification: str
    groups: Tuple[str, ...] = ()
    effect: Tuple = ()              # ("costume", wram) / ("map_fragment", stage_index) / ("coins", amount) / ...


ITEMS = [
    # Costumes: the client writes 1 to the ownership flag
    ItemData(I.wizard_costume, 0, PROGRESSION, (G_COSTUMES,), ("costume", 0x7E02C1)),
    ItemData(I.firefighter_costume, 1, PROGRESSION, (G_COSTUMES,), ("costume", 0x7E02C2)),
    ItemData(I.mountaineer_costume, 2, PROGRESSION, (G_COSTUMES,), ("costume", 0x7E02C3)),
    # Map Fragments: bit n of AP RAM $7FEE00 = Stage Index n (Pete's Castle is Stage Index 6)
    ItemData(I.treetops_map_fragment, 10, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_TREETOPS)),
    ItemData(I.dark_forest_map_fragment, 11, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_DARK_FOREST)),
    ItemData(I.fire_grotto_map_fragment, 12, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_FIRE_GROTTO)),
    ItemData(I.petes_peak_map_fragment, 13, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_PETES_PEAK)),
    ItemData(I.snowy_valley_map_fragment, 14, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_SNOWY_VALLEY)),
    ItemData(I.petes_castle_map_fragment, 15, PROGRESSION, (G_MAP_FRAGMENTS,), ("map_fragment", STAGE_PETES_CASTLE)),
    # Mickey Coins: add the amount to $02A8-$02AA with carry, clamp at 999. Only the 300 is progression (one copy).
    ItemData(I.coins_300, 20, PROGRESSION, (G_COINS,), ("coins", 300)),
    ItemData(I.coins_100, 21, FILLER, (G_COINS,), ("coins", 100)),
    ItemData(I.coins_50, 22, FILLER, (G_COINS,), ("coins", 50)),
    ItemData(I.coins_20, 23, FILLER, (G_COINS,), ("coins", 20)),
    ItemData(I.coins_12, 24, FILLER, (G_COINS,), ("coins", 12)), # 12 is the amount of coins Treasure Boxes drop in the vanilla game.
    ItemData(I.coins_200, 25, USEFUL, (G_COINS,), ("coins", 200)),     
    # Pete's Emblem: increments the count the client mirrors to AP RAM $7FEE0D
    ItemData(I.petes_emblem, 30, PROGRESSION, (), ("emblem",)),
    # Useful
    ItemData(I.big_heart, 40, USEFUL, (), ("big_heart",)),
    ItemData(I.magic_upgrade, 41, USEFUL, (G_UPGRADES,), ("upgrade", 0x7E02B5)),
    ItemData(I.water_upgrade, 42, USEFUL, (G_UPGRADES,), ("upgrade", 0x7E02B6)),
    # Filler
    ItemData(I.magic_lamp, 50, FILLER, (G_REFILLS,), ("refill", 0x7E02B7, 8)),
    ItemData(I.fire_hydrant, 51, FILLER, (G_REFILLS,), ("refill", 0x7E02B9, 8)),
    ItemData(I.small_heart, 52, FILLER, (G_REFILLS,), ("heal", 1)),
    ItemData(I.mickey_doll, 53, FILLER, (), ("life",)),
]

# The goal Event item: no AP ID (id None). Emperor Pete event Location.
EVENT_ITEM = I.victory

ITEM_BY_NAME = {item.name: item for item in ITEMS}

# Pool rules that do not depend on options (counts that do, such as Big Hearts, are computed in __init__.py)
MAP_FRAGMENT_COUNT = 6
EMBLEM_COUNT = 5                   # one per main Stage Boss, locked on those five Locations
SINGLE_COPY = (I.coins_300, I.magic_upgrade, I.water_upgrade)
TWO_COPIES = (I.coins_200,)         # Useful: two copies of 200 Mickey Coins
FILLER_ITEMS = [item.name for item in ITEMS if item.classification == FILLER]

# Filler weights (relative; equal for simplicity, but increasing coin weight is a possibility)
FILLER_WEIGHTS = {name: 1 for name in FILLER_ITEMS}
