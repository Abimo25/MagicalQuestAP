# =========
# = Items =
# =========
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Set

from BaseClasses import Item, ItemClassification

from .data import items_data as data
from .names import GAME_NAME
from .names import item_name as I

if TYPE_CHECKING:
    from . import MagicalQuestWorld

item_name_to_id: Dict[str, int] = {item.name: data.STARTING_ID + item.id_offset for item in data.ITEMS}

CLASSIFICATION = {
    data.PROGRESSION: ItemClassification.progression,
    data.USEFUL: ItemClassification.useful,
    data.FILLER: ItemClassification.filler,
}


def _item_groups() -> Dict[str, Set[str]]:
    groups: Dict[str, Set[str]] = {}
    for item in data.ITEMS:
        for group in item.groups:
            groups.setdefault(group, set()).add(item.name)
    return groups


ITEM_NAME_GROUPS = _item_groups()


class MagicalQuestItem(Item):
    game = GAME_NAME


def create_item(world: MagicalQuestWorld, name: str) -> MagicalQuestItem:
    if name == data.EVENT_ITEM:                       # the goal Event item has no ID
        return MagicalQuestItem(name, ItemClassification.progression, None, world.player)
    item = data.ITEM_BY_NAME[name]
    return MagicalQuestItem(name, CLASSIFICATION[item.classification], item_name_to_id[name], world.player)


def get_random_filler_item_name(world: MagicalQuestWorld) -> str:
    names = list(data.FILLER_WEIGHTS)
    return world.random.choices(names, weights=[data.FILLER_WEIGHTS[n] for n in names])[0]


def create_all_items(world: MagicalQuestWorld) -> None:
    # Fill the pool: one copy of each fixed item, the Big Hearts are the Starting Max Health asks for -10, then filler.
    # Not in the pool: the five Pete's Emblems (locked on the boss Locations, Locations.py), the Map Fragments in the
    # start inventory and whatever the Game Mode locks on a Location (Linear: the Fragments, Vanilla Progression: the
    # Costumes as well); generate_early decides all of these."""
    pool: List[Item] = []
    elsewhere = set(world.precollected_fragments) | set(world.locked_items.values())     # Game Mode
    for name in (I.wizard_costume, I.firefighter_costume, I.mountaineer_costume):
        if name not in elsewhere:
            pool.append(world.create_item(name))
    for name in I.map_fragments:
        if name not in elsewhere:
            pool.append(world.create_item(name))
    for name in data.SINGLE_COPY:                     # 300 Mickey Coins, Magic Upgrade, Water Upgrade
        pool.append(world.create_item(name))
    for name in data.TWO_COPIES:                      # 200 Mickey Coins (Useful), twice
        pool += [world.create_item(name), world.create_item(name)]
    for _ in range(10 - world.options.starting_max_health.value):
        pool.append(world.create_item(I.big_heart))

    free_locations = len(world.multiworld.get_unfilled_locations(world.player))
    pool += [world.create_filler() for _ in range(free_locations - len(pool))]
    world.multiworld.itempool += pool