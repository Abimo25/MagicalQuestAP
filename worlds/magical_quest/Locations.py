# =============
# = Locations =
# =============
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from BaseClasses import Location, LocationProgressType

from .data import locations_data as data
from .data.items_data import STARTING_ID
from .names import GAME_NAME
from .names import item_name as I
from .names import location_name as L
from .Items import MagicalQuestItem

if TYPE_CHECKING:
    from . import MagicalQuestWorld

location_name_to_id: Dict[str, int] = {loc.name: STARTING_ID + loc.id_offset for loc in data.LOCATIONS}
LOCATION_NAME_GROUPS = data.location_groups()


class MagicalQuestLocation(Location):
    game = GAME_NAME


def create_all_locations(world: MagicalQuestWorld) -> None:
    # Add every Location to its Region, lock the five Pete's Emblems to the boss Locations and create the goal Event.
    box_is_filler = bool(world.options.hard_only_box_filler)
    for loc in data.LOCATIONS:
        region = world.get_region(loc.region)
        location = MagicalQuestLocation(world.player, loc.name, location_name_to_id[loc.name], region)
        if loc.hard_only and box_is_filler:
            # Treetops 1-2 Box B can only be acquired on Hard: keep progression and useful items out of it.
            location.progress_type = LocationProgressType.EXCLUDED
        region.locations.append(location)

    for name in data.EMBLEM_LOCATIONS: # each boss yields its own Emblem
        world.get_location(name).place_locked_item(world.create_item(I.petes_emblem))

    for location_name, item_name in world.locked_items.items(): # Game Mode: Linear and Vanilla Progression
        world.get_location(location_name).place_locked_item(world.create_item(item_name))

    world.get_region(data.EVENT_REGION).add_event(
        L.emperor_pete_event, I.victory, location_type=MagicalQuestLocation, item_type=MagicalQuestItem)
