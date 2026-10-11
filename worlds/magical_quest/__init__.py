# ==============================================================================
# = The Magical Quest Starring Mickey Mouse (SNES) Archipelago Implementation. =
# ==============================================================================
from __future__ import annotations

import base64
import os
from typing import Any, ClassVar, Dict, List

from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld, World

from . import Items, Locations, Regions, Rom, Rules
from .Client import MagicalQuestSNIClient
from .data import items_data, locations_data
from .names import GAME_NAME, WORLD_VERSION
from .Options import GameMode, MagicalQuestOptions
from .Ram import STAGE_TREETOPS
from .Rom import MagicalQuestSettings


class MagicalQuestWebWorld(WebWorld):
    theme = "grass"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up The Magical Quest Starring Mickey Mouse for Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["e.cortes"],
    )]


class MagicalQuestWorld(World):
    """
    The Magical Quest Starring Mickey Mouse is a 1992 SNES platformer developed by Capcom.
    Pluto has disappeared and his pal Mickey is hot on his trail!
    Pluto's tracks lead Mickey to a magical world full of perils.
    As he travels through the land, Mickey meets a kind, old wizard who tells him that the
    evil Emperor Pete has snatched poor Pluto!
    Summoning his courage, Mickey vows to free his pal and sets off toward Emperor Pete's Castle.
    Along his treacherous trek, Mickey will find three special costumes which will aid him in his journey.
    Wizard Costume - allows Mickey to attack with magic and breathe underwater.
    Firefighter Costume - allows Mickey to shoot water to put out fire and push blocks.
    Mountaineer Costume - allows Mickey to use a grappling hook to scale mountains and traverse rough terrain.
    """
    game = GAME_NAME
    web = MagicalQuestWebWorld()
    topology_present = False

    settings: ClassVar[MagicalQuestSettings]
    options_dataclass = MagicalQuestOptions
    options: MagicalQuestOptions

    item_name_to_id: ClassVar[Dict[str, int]] = Items.item_name_to_id
    location_name_to_id: ClassVar[Dict[str, int]] = Locations.location_name_to_id
    item_name_groups = Items.ITEM_NAME_GROUPS
    location_name_groups = Locations.LOCATION_NAME_GROUPS

    starting_stage_index: int
    starting_map_fragment: str
    precollected_fragments: List[str]        # the Map Fragments in the start inventory (not in the pool)
    locked_items: Dict[str, str]             # Location name -> Item name placed there at generation (Game Mode)
    ut_can_gen_without_yaml = True

    @staticmethod
    def interpret_slot_data(slot_data: Dict[str, Any]) -> Dict[str, Any]:
        return slot_data

    def apply_passthrough(self) -> None:
        passthrough = getattr(self.multiworld, "re_gen_passthrough", {})
        if passthrough and self.game in passthrough:
            for key, value in passthrough[self.game].get("options", {}).items():
                option = getattr(self.options, key, None)
                if option is not None:
                    setattr(self.options, key, option.from_any(value))

    def generate_early(self) -> None:
        self.apply_passthrough()
        # The Stage Index is the option value; the Stage's Map Fragment is precollected, not in the item pool.
        mode = self.options.game_mode.value
        stage = self.options.starting_stage.value
        if mode != GameMode.option_map_fragments:
            stage = STAGE_TREETOPS # the Starting Stage option only makes sense in Map Fragments mode, otherwise Treetops is set as the actual "starting stage".
        # Write the effective Stage back, so the slot data carry what was really used.
        self.options.starting_stage.value = stage
        self.starting_stage_index = stage
        self.starting_map_fragment = self.fragment_of_stage(stage)

        self.precollected_fragments = [self.starting_map_fragment]
        self.locked_items = {}
        if mode == GameMode.option_open_world:
            self.precollected_fragments = list(locations_data.OPEN_WORLD_FRAGMENTS)
        elif mode in (GameMode.option_linear, GameMode.option_vanilla_progression):
            self.locked_items.update(locations_data.LINEAR_CLEAR_UNLOCKS)
            if mode == GameMode.option_vanilla_progression:
                self.locked_items.update(locations_data.VANILLA_COSTUME_UNLOCKS)
        for name in self.precollected_fragments:
            self.push_precollected(self.create_item(name))

    @staticmethod
    def fragment_of_stage(stage_index: int) -> str:
        return next(item.name for item in items_data.ITEMS
                    if item.effect[:1] == ("map_fragment",) and item.effect[1] == stage_index)

    def create_regions(self) -> None:
        Regions.create_and_connect_regions(self)
        Locations.create_all_locations(self)

    def create_items(self) -> None:
        Items.create_all_items(self)

    def set_rules(self) -> None:
        Rules.set_all_rules(self)

    def create_item(self, name: str) -> Items.MagicalQuestItem:
        return Items.create_item(self, name)

    def get_filler_item_name(self) -> str:
        return Items.get_random_filler_item_name(self)

    def generate_output(self, output_directory: str) -> None:
        patch = Rom.MagicalQuestProcedurePatch(player=self.player, player_name=self.player_name)
        Rom.patch_rom(self, patch)
        file_name = f"{self.multiworld.get_out_file_name_base(self.player)}{patch.patch_file_ending}"
        patch.write(os.path.join(output_directory, file_name))

    def modify_multidata(self, multidata: Dict[str, Any]) -> None:
        identity = Rom.identity_bytes(self.player_name, str(self.multiworld.seed_name))
        multidata["connect_names"][base64.b64encode(identity).decode()] = multidata["connect_names"][self.player_name]

    def fill_slot_data(self) -> Dict[str, Any]:
        # What the client reads on connect: the choices the ROM already carries are repeated so a client can check
        # them against the patched ROM before it writes anything.
        return {
            "options": self.options.as_dict("game_mode", "starting_stage", "starting_max_health", "hard_only_box_filler",
                                            "store_hints"),
            "world_version": WORLD_VERSION,
            "game_mode": self.options.game_mode.value,
            "starting_stage": self.starting_stage_index,
            "starting_max_health": self.options.starting_max_health.value,
            "hard_only_box_filler": bool(self.options.hard_only_box_filler),
            "store_hints": bool(self.options.store_hints),
        }


