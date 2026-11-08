# =================
# = ROM Addresses =
# =================
# The layout of the data Python writes into the ROM.
# Addresses are FILE OFFSETS in the headerless 2MB ROM unless a name says "cpu". LoROM: file offset =
# (bank & 0x7F) * 0x8000 + (address & 0x7FFF). The new code and the config block live in banks $20+ (file
# $100000 and up), created by expanding the ROM to 2MB. The patch is a pre-built diff of a patched ROM.
# Python only overwrites the baked bytes below at seed generation.


# ---- Base ROM (the unmodified 1 MB dump the player supplies) ---------------------------------------
BASE_ROM_SIZE = 0x100000
PATCHED_ROM_SIZE = 0x200000
BASE_ROM_MD5 = "649c377a7479c898b1933962c4badaad"   # MD5 of the unmodified 1 MB dump (also goes into docs/setup_en.md)

# ---- Header ---------------------------------------------------------------------------------------
HEADER_TITLE_OFFSET = 0x7FC0   # 21 bytes, the SNES internal title ($00:FFC0)
HEADER_TITLE_LENGTH = 21
ROM_SIZE_BYTE_OFFSET = 0x7FD7  # set to $0B after the ROM was expanded to 2MB

# ---- Config block written by patch_rom ------------------------------------------------------------
CONFIG_BASE = 0x100000         # cpu $20:8000
CONFIG_SIGNATURE = b"MQAP"     # $208000
CONFIG_FORMAT_VERSION = 0x01   # $208004
CONFIG_START_STAGE_OFFSET = CONFIG_BASE + 0x05        # $208005: Stage Index of the starting Map Fragment
CONFIG_SKATER_HP_OFFSET = CONFIG_BASE + 0x06          # $208006: 1 = lower the 5-3 Skater's HP without W or F
CONFIG_ENTRY_LEVEL_OFFSET = CONFIG_BASE + 0x08        # $208008-$20800E: entry Level Index by Stage Index 0..6
CONFIG_ENTRY_LEVELS_DEFAULT = bytes([0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x01])

# Starting Max Health: the four entries of the vanilla difficulty table at cpu $00:CCF7 (file $4CF7)
MAX_HEALTH_TABLE_OFFSET = 0x4CF7
MAX_HEALTH_TABLE_LENGTH = 4

# ---- Identity block (Python only: no ROM code reads it; the client reads it to find the seed and the slot) --
IDENTITY_BASE = CONFIG_BASE + 0x10
SLOT_NAME_OFFSET = IDENTITY_BASE            # $208010, 16 bytes, zero padded: the AP slot name (auth)
SLOT_NAME_LENGTH = 16
SEED_NAME_OFFSET = IDENTITY_BASE + 0x10     # $208020, 21 bytes, zero padded: the multiworld seed name
SEED_NAME_LENGTH = 21
# The header title carries "MQAP" + the world version, so SNI clients can recognise the ROM before reading more.

# ---- Treasure Box item classes -------------------------------------------
# One byte per box number (the order of names/location_name.py): the icon of the AP Item the box drops
# Debug: The base patch cycles 0, 1, 2 so every icon can be seen without a seed.
BOX_CLASS_OFFSET = CONFIG_BASE + 0xB50      # cpu $208B50 (ClassTable)
BOX_CLASS_COUNT = 37
BOX_CLASS_FILLER = 0
BOX_CLASS_USEFUL = 1
BOX_CLASS_PROGRESSION = 2

# ---- Store Location item classes ---------------------------------------------
# One byte per Store latch bit: 0 Dark Forest Big Heart, 1 Pete's Castle Big Heart, 2 Magic Upgrade,
# 3 Water Upgrade, 4 Treetops, 5 Fire Grotto, 6 Pete's Peak Big Heart), same values as the boxes.
STORE_CLASS_OFFSET = CONFIG_BASE + 0x1600   # cpu $209600 (StoreClass)
STORE_CLASS_COUNT = 7



