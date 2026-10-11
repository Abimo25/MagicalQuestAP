# ================
# = Region Names =
# ================
# Regions are cumulative: each Level region is entered from the previous Level of the same Stage with the rule "clear that Level",
# so a Location's rule only needs its own requirement plus the Stage's Map Fragment. 
# Rules assume every visit to a Stage starts at 1-1.

menu = "Menu"

# Stage regions (entered with the Stage's Map Fragment)
treetops = "Treetops"
dark_forest = "Dark Forest"
fire_grotto = "Fire Grotto"
petes_peak = "Pete's Peak"
snowy_valley = "Snowy Valley"
petes_castle = "Pete's Castle"

# Level regions
treetops_1_1 = "Treetops 1-1"
treetops_1_2 = "Treetops 1-2"
treetops_1_3 = "Treetops 1-3"
treetops_1_4 = "Treetops 1-4"           # boss Level
dark_forest_2_1 = "Dark Forest 2-1" 
dark_forest_2_2 = "Dark Forest 2-2" 
dark_forest_2_3 = "Dark Forest 2-3" 
dark_forest_2_4 = "Dark Forest 2-4"     # boss Level
fire_grotto_3_1 = "Fire Grotto 3-1" 
fire_grotto_3_2 = "Fire Grotto 3-2" 
fire_grotto_3_3 = "Fire Grotto 3-3" 
fire_grotto_3_4 = "Fire Grotto 3-4"     # boss Level
petes_peak_4_1 = "Pete's Peak 4-1" 
petes_peak_4_2 = "Pete's Peak 4-2" 
petes_peak_4_3 = "Pete's Peak 4-3"      # boss Level
snowy_valley_5_1 = "Snowy Valley 5-1" 
snowy_valley_5_2 = "Snowy Valley 5-2" 
snowy_valley_5_3 = "Snowy Valley 5-3"   # boss Level
petes_castle_6_1 = "Pete's Castle 6-1" 
petes_castle_6_2 = "Pete's Castle 6-2" 
petes_castle_6_3 = "Pete's Castle 6-3" 
petes_castle_6_4 = "Pete's Castle 6-4"  # Emperor Pete

# Stores (Store 01-05): each has its own access rule.
treetops_store = "Treetops Store"
dark_forest_store = "Dark Forest Store"
fire_grotto_store = "Fire Grotto Store"
petes_peak_store = "Pete's Peak Store"
petes_castle_store = "Pete's Castle Store"
# "Reaching any Store": reachable from each Store region; holds the two shared Upgrade Locations
general_store = "General Store"