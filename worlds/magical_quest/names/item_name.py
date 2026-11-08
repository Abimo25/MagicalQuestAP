# ==============
# = Item Names =
# ==============
# The strings are what the AP Server and the AP Client show.
# All coin items are named exactly "[amount] Mickey Coins", whether progression, useful or filler.

# Progression: Costumes (written to $7E02C1-$7E02C3 by the client)
wizard_costume = "Wizard Costume"
firefighter_costume = "Firefighter Costume"
mountaineer_costume = "Mountaineer Costume"
# Progressive Costumes option: two copies each; the first is the Costume, the second its Upgrade (Magic / Water)
progressive_wizard = "Progressive Wizard"
progressive_firefighter = "Progressive Firefighter"

# Progression: Map Fragments, one per Stage (AP RAM $7FEE00, bit n = Stage Index n)
treetops_map_fragment = "Treetops Map Fragment"
dark_forest_map_fragment = "Dark Forest Map Fragment"
fire_grotto_map_fragment = "Fire Grotto Map Fragment"
petes_peak_map_fragment = "Pete's Peak Map Fragment"
snowy_valley_map_fragment = "Snowy Valley Map Fragment"
petes_castle_map_fragment = "Pete's Castle Map Fragment"

# Progression: two copies in the pool; logic asks for one before any Store Location, so the player never has to grind coins when many important items happen to be in the Stores.
coins_300 = "300 Mickey Coins"

# Progression: 5 guaranteed, one per main Stage Boss.
petes_emblem = "Pete's Emblem"

# Useful
big_heart = "Big Heart"                 # Max Health +1; pool size changes depending on the user YAML.
magic_upgrade = "Magic Upgrade"         # one copy
water_upgrade = "Water Upgrade"         # one copy

# Useful: two copies in the pool
coins_200 = "200 Mickey Coins"

# Filler
coins_100 = "100 Mickey Coins"
coins_50 = "50 Mickey Coins"
coins_20 = "20 Mickey Coins"
coins_12 = "12 Mickey Coins"            # 12 is the amount of coins Treasure Boxes drop in the vanilla game.
magic_lamp = "Magic Lamp"
fire_hydrant = "Fire Hydrant"
small_heart = "Small Heart"
mickey_doll = "Mickey Doll"

# Event item (no AP ID): the goal
victory = "Victory"

map_fragments = [
    treetops_map_fragment, dark_forest_map_fragment, fire_grotto_map_fragment,
    petes_peak_map_fragment, snowy_valley_map_fragment, petes_castle_map_fragment,
]  # in Stage Index order (0-5 in the AP RAM bit order is decided in Ram.py, not here)
