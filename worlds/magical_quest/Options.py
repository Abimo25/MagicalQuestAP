# ===========
# = Options =
# ===========
from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, PerGameCommonOptions, Range, StartInventoryPool

from .Ram import (STAGE_TREETOPS, STAGE_DARK_FOREST, STAGE_FIRE_GROTTO, STAGE_PETES_PEAK, STAGE_SNOWY_VALLEY,
                  STAGE_PETES_CASTLE)


class GameMode(Choice):
    """How the Stages open up.

    Map Fragments: You start with one Stage, and each Stage is locked behind an AP Item called "Map Fragment", shuffled into the multiworld.
    You are guaranteed to always start with a Map Fragment. Recommended for playing alongside other games.

    Open World: All Stages are available from the beginning: Treetops, Dark Forest, Fire Grotto, Pete's Peak and Snowy Valley.
    Only the Pete's Castle Map Fragment has to be found in the multiworld. Recommended for synchronous play.

    Linear: You start in Treetops. Clearing a Stage unlocks the next one, in the vanilla game's order.
    (Treetops -> Dark Forest -> Fire Grotto -> Pete's Peak -> Snowy Valley -> Pete's Castle).

    Vanilla Progression: Like Linear, but each Costume is also on its vanilla Stage
    (Wizard in Dark Forest, Firefighter in Fire Grotto, Mountaineer in Pete's Peak).
    Costumes are received on Stage entry. You will likely end before other Players."""
    display_name = "Game Mode"
    option_map_fragments = 0
    option_open_world = 1
    option_linear = 2
    option_vanilla_progression = 3
    default = 0


class StartingStage(Choice):
    """The Stage you start in. 
    This only applies to the Map Fragments Game Mode.
    Recommended: Random."""
    display_name = "Starting Stage"
    # The values are the actual game's Stage Index value (Pete's Castle is 6, not 5).
    option_treetops = STAGE_TREETOPS
    option_dark_forest = STAGE_DARK_FOREST
    option_fire_grotto = STAGE_FIRE_GROTTO
    option_petes_peak = STAGE_PETES_PEAK
    option_snowy_valley = STAGE_SNOWY_VALLEY
    option_petes_castle = STAGE_PETES_CASTLE
    default = "random"


class StartingMaxHealth(Range):
    """The number of Big Hearts Mickey starts with (1 to 10). The rest of the Big Hearts are placed in the pool.
    The vanilla game starts with 3 on Normal and 2 on Hard. Only choose 1 if you hate your own guts."""
    display_name = "Starting Max Health"
    range_start = 1
    range_end = 10
    default = 3


class HardOnlyBoxFiller(DefaultOnToggle):
    """Treetops 1-2 has a Treasure Box that can only be reached when the game is played on Hard difficulty.
    Turn this is on so that Location only holds filler items. Turn it off if you plan to play on Hard: it becomes a normal Location.
    You choose the difficulty in the game's own options menu."""
    display_name = "Hard-only Box Holds Filler"


class StoreHints(DefaultOnToggle):
    """When you enter a Store, the client sends hints for what you would get from it: the two Upgrades in every Store,
    and the two Big Hearts in their respective Stores. Everyone in the multiworld sees them, whichever game
    the item belongs to. Turn this off if you would rather find out what the Store holds by buying it."""
    display_name = "Store Hints"


@dataclass
class MagicalQuestOptions(PerGameCommonOptions):
    game_mode: GameMode
    starting_stage: StartingStage
    starting_max_health: StartingMaxHealth
    hard_only_box_filler: HardOnlyBoxFiller
    store_hints: StoreHints
    start_inventory_from_pool: StartInventoryPool