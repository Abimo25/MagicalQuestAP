# ===========
# = Regions =
# ===========
# The rules on the connections are set in Rules.py.

from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Region

from .data import gates_data as gates
from .data import regions_data as data
from .names import region_name as R

if TYPE_CHECKING:
    from . import MagicalQuestWorld


def entrance_name(source: str, target: str) -> str:
    return f"{source} -> {target}"


def create_and_connect_regions(world: MagicalQuestWorld) -> None:
    for name in data.ALL_REGIONS:
        world.multiworld.regions.append(Region(name, world.player, world.multiworld))

    def connect(source: str, target: str) -> None:
        world.get_region(source).connect(world.get_region(target), entrance_name(source, target))

    for stage, levels in gates.STAGE_LEVELS.items():
        connect(R.menu, stage)                        # rule: the Stage's Map Fragment
        connect(stage, levels[0])                     # every visit starts at 1-1, no rule
    for source, target, _ in gates.LEVEL_EXITS:
        connect(source, target)
    for level, store, _ in gates.STORE_DOORS:
        connect(level, store)
        connect(store, R.general_store)