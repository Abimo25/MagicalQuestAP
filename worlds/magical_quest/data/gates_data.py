# ====================
# = RULE EXPRESSIONS =
# ====================
# Short strings, parsed once by Rules.py:
# - ""            no requirement (Normal Mickey can do it).
# - "W" "F" "M"   owns the Wizard / Firefighter / Mountaineer Costume.
# - "COINS"       owns the "300 Mickey Coins" item (to make sure the player can always afford to buy one Store Location).
# - "EMBLEMS"     have received 5 Pete's Emblems (entering the 6-4 Pete Statue will without 5 or more of these will send the player back to 6-3).
# A Location rule is only its OWN requirement; what the Level before it demands is the rule on
# the connection INTO its Level region, and the Stage's Map Fragment is the rule on the
# connection into the Stage region.
# The Emperor Pete Statue is gated behind aquiring all 5 Emblems.

from ..names import item_name as I
from ..names import region_name as R

TOKENS = {
    "W": I.wizard_costume,
    "F": I.firefighter_costume,
    "M": I.mountaineer_costume,
    "COINS": I.coins_300,
    "EMBLEMS": I.petes_emblem,
}
EMBLEMS_REQUIRED = 5

# Stage region -> the Map Fragment item that opens it (connection Menu -> Stage).
STAGE_ENTRY = {
    R.treetops: I.treetops_map_fragment,
    R.dark_forest: I.dark_forest_map_fragment,
    R.fire_grotto: I.fire_grotto_map_fragment,
    R.petes_peak: I.petes_peak_map_fragment,
    R.snowy_valley: I.snowy_valley_map_fragment,
    R.petes_castle: I.petes_castle_map_fragment,
}

# Stage region -> its Level regions in order. The first Level is entered from the Stage region with no rule.
# Level is considered to always start at 1 and the boss Level is the last one (6-4 for Pete's Castle).
STAGE_LEVELS = {
    R.treetops: [R.treetops_1_1, R.treetops_1_2, R.treetops_1_3, R.treetops_1_4],
    R.dark_forest: [R.dark_forest_2_1, R.dark_forest_2_2, R.dark_forest_2_3, R.dark_forest_2_4],
    R.fire_grotto: [R.fire_grotto_3_1, R.fire_grotto_3_2, R.fire_grotto_3_3, R.fire_grotto_3_4],
    R.petes_peak: [R.petes_peak_4_1, R.petes_peak_4_2, R.petes_peak_4_3],
    R.snowy_valley: [R.snowy_valley_5_1, R.snowy_valley_5_2, R.snowy_valley_5_3],
    R.petes_castle: [R.petes_castle_6_1, R.petes_castle_6_2, R.petes_castle_6_3, R.petes_castle_6_4],
}

# (from, to, rule): what clearing the FROM Level requires.
LEVEL_EXITS = [
    (R.treetops_1_1, R.treetops_1_2, ""),
    (R.treetops_1_2, R.treetops_1_3, ""),
    (R.treetops_1_3, R.treetops_1_4, ""),
    (R.dark_forest_2_1, R.dark_forest_2_2, ""),
    (R.dark_forest_2_2, R.dark_forest_2_3, "W"),            # Hollow Tree.
    (R.dark_forest_2_3, R.dark_forest_2_4, ""),
    (R.fire_grotto_3_1, R.fire_grotto_3_2, ""),             # It's possible to beat the Mini-boss with any Costume with the patched Red Blocks.
    (R.fire_grotto_3_2, R.fire_grotto_3_3, "F | M"),        # A Grey Block is in the way.
    (R.fire_grotto_3_3, R.fire_grotto_3_4, "F | M"),        # Grey Block Wall.
    (R.petes_peak_4_1, R.petes_peak_4_2, "M"),              # Mountain hike.
    (R.petes_peak_4_2, R.petes_peak_4_3, ""),
    (R.snowy_valley_5_1, R.snowy_valley_5_2, ""),
    (R.snowy_valley_5_2, R.snowy_valley_5_3, ""),
    (R.petes_castle_6_1, R.petes_castle_6_2, ""),
    (R.petes_castle_6_2, R.petes_castle_6_3, "W"),          # Magic Carpet.
    (R.petes_castle_6_3, R.petes_castle_6_4, "F & EMBLEMS"),  # Moving Blocks (F) + the Emperor Pete Statue gate.
]

# Store doors: (Level region holding the Magic Door, Store region, rule to reach the door).
STORE_DOORS = [
    (R.treetops_1_2, R.treetops_store, ""),
    (R.dark_forest_2_2, R.dark_forest_store, "W"),          # After the Hollow Tree.
    (R.fire_grotto_3_3, R.fire_grotto_store, ""),           # Level entry already needs F | M.
    (R.petes_peak_4_1, R.petes_peak_store, "M"),            # Needs to clim the mountain Mountain.
    (R.petes_castle_6_1, R.petes_castle_store, ""),         # Underwater, but Normal Mickey can reach it.
]
# Every Store region leads to the shared "General Store" region (the two Upgrade Locations), rule "".

