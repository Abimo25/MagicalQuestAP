# ================
# = ROM Patching =
# ================
# The ROM is a premade patch (bsdiff4) of my own dump.
# There's a small token file with what changes per seed:
# the starting Stage, the starting Max Health, the header title and the identity block.
# Last comes the SNES checksum, which the header edit invalidates.
# The patch container is an Archipelago procedure patch (.apmq): "apply_bsdiff4" on the base dump, "apply_tokens", "apply_checksum".

from __future__ import annotations

import hashlib
import os
import pkgutil
from typing import TYPE_CHECKING, Any, Optional, Sequence, Tuple

import settings
import Utils
from worlds.Files import APPatchExtension, APProcedurePatch, APTokenMixin, APTokenTypes

from . import RomData
from .names import GAME_NAME, WORLD_VERSION

if TYPE_CHECKING:
    from . import MagicalQuestWorld

BASE_PATCH_FILE = "mq_base_patch.bsdiff4"          # in data/, built from the developer's patched ROM
BASE_PATCH_RESOURCE = f"data/{BASE_PATCH_FILE}"
TOKEN_FILE = "token_patch.bin"
COPIER_HEADER_SIZE = 0x200
LOROM_BANK_SIZE = 0x8000
CHECKSUM_OFFSET = 0x7FDC                           # complement (2 bytes) then checksum (2 bytes), little endian


# ---- Base ROM ----------------------------------------------------------------------------------------
def strip_copier_header(data: bytes) -> bytes:
    # Dumps with a 512-byte copier header are accepted: the patch is made from the headerless dump.
    if len(data) % LOROM_BANK_SIZE == COPIER_HEADER_SIZE:
        return data[COPIER_HEADER_SIZE:]
    return data


def read_base_rom(path: str) -> bytes:
    # The headerless base dump, checked against RomData.BASE_ROM_MD5.
    with open(path, "rb") as file:
        data = strip_copier_header(file.read())
    digest = hashlib.md5(data).hexdigest()
    if digest != RomData.BASE_ROM_MD5:
        raise ValueError(f"The base ROM {path} has MD5 {digest}, expected {RomData.BASE_ROM_MD5}. "
                         f"Use an unmodified dump of the US version of The Magical Quest Starring Mickey Mouse.")
    return data


def get_base_rom_path(file_name: str = "") -> str:
    if not file_name:
        file_name = settings.get_settings()["magical_quest_options"]["rom_file"]
    if not os.path.exists(file_name):
        file_name = Utils.user_path(file_name)
    return file_name


def get_base_rom_bytes(file_name: str = "") -> bytes:
    cached: Optional[bytes] = getattr(get_base_rom_bytes, "base_rom_bytes", None)
    if cached is None:
        cached = read_base_rom(get_base_rom_path(file_name))
        setattr(get_base_rom_bytes, "base_rom_bytes", cached)
    return cached


class MagicalQuestSettings(settings.Group):
    class RomFile(settings.UserFilePath):
        # File name of the unmodified US ROM of Magical Quest
        description = "The Magical Quest Starring Mickey Mouse ROM file"
        copy_to: Optional[str] = "The Magical Quest Starring Mickey Mouse (USA).sfc"
        md5s = [RomData.BASE_ROM_MD5]

        def browse(self: settings.T, filetypes: Optional[Sequence[Tuple[str, Sequence[str]]]] = None,
                   **kwargs: Any) -> Optional[settings.T]:
            return super().browse(filetypes or [("SNES", [".sfc", ".smc"])], **kwargs)

        @classmethod
        def validate(cls, path: str) -> None:
            read_base_rom(path)                               # raises ValueError on a wrong dump

    rom_file: RomFile = RomFile(RomFile.copy_to)


# ---- Patch container and steps -----------------------------------------------------------------------
class MagicalQuestPatchExtension(APPatchExtension):
    game = GAME_NAME

    @staticmethod
    def apply_checksum(caller: APProcedurePatch, rom: bytes) -> bytes:
        # Recompute the SNES internal checksum (the ROM is 2 MB, a power of two, so a plain byte sum is right).
        data = bytearray(rom)
        data[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 4] = b"\xFF\xFF\x00\x00"
        checksum = sum(data) & 0xFFFF
        data[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 4] = ((checksum ^ 0xFFFF).to_bytes(2, "little")
                                                      + checksum.to_bytes(2, "little"))
        return bytes(data)


class MagicalQuestProcedurePatch(APProcedurePatch, APTokenMixin):
    hash = RomData.BASE_ROM_MD5
    game = GAME_NAME
    patch_file_ending = ".apmq"
    result_file_ending = ".sfc"
    procedure = [
        ("apply_bsdiff4", [BASE_PATCH_FILE]),
        ("apply_tokens", [TOKEN_FILE]),
        ("apply_checksum", []),
    ]

    @classmethod
    def get_source_data(cls) -> bytes:
        return get_base_rom_bytes()

    def write_byte(self, offset: int, value: int) -> None:
        self.write_token(APTokenTypes.WRITE, offset, value.to_bytes(1, "little"))

    def write_bytes(self, offset: int, value: bytes) -> None:
        self.write_token(APTokenTypes.WRITE, offset, bytes(value))


def padded(text: str, length: int, fill: bytes) -> bytes:
    # ASCII text cut to "length" and padded with "fill" (zero for the identity block, a space for the header title).
    return text.encode("ascii", "replace")[:length].ljust(length, fill)


def identity_bytes(slot_name: str, seed_name: str) -> bytes:
    # The 37-byte identity block (slot name 16 + seed name 21, zero padded). The client sends base64 of it as the
    # connect name, and modify_multidata maps the same string to the slot.
    return (padded(slot_name, RomData.SLOT_NAME_LENGTH, b"\x00") + padded(seed_name, RomData.SEED_NAME_LENGTH, b"\x00"))


def write_seed_tokens(patch: MagicalQuestProcedurePatch, starting_stage: int, starting_max_health: int,
                      slot_name: str, seed_name: str) -> None:
    # This is everything a seed changes, as WRITE tokens (offsets in RomData).
    patch.write_byte(RomData.CONFIG_START_STAGE_OFFSET, starting_stage)
    patch.write_bytes(RomData.CONFIG_ENTRY_LEVEL_OFFSET, RomData.CONFIG_ENTRY_LEVELS_DEFAULT)
    patch.write_bytes(RomData.MAX_HEALTH_TABLE_OFFSET, bytes([starting_max_health]) * RomData.MAX_HEALTH_TABLE_LENGTH)
    patch.write_bytes(RomData.HEADER_TITLE_OFFSET,
                      padded(f"MQAP {WORLD_VERSION}", RomData.HEADER_TITLE_LENGTH, b" "))
    patch.write_bytes(RomData.IDENTITY_BASE, identity_bytes(slot_name, seed_name))


def patch_rom(world: MagicalQuestWorld, patch: MagicalQuestProcedurePatch) -> None:
    base_patch = pkgutil.get_data(__name__, BASE_PATCH_RESOURCE)
    if base_patch is None:
        raise FileNotFoundError(f"{BASE_PATCH_RESOURCE} is missing from the world: build it from the patched ROM "
                                f"(Part 3, ROM patch pipeline).")
    patch.write_file(BASE_PATCH_FILE, base_patch)
    write_seed_tokens(patch, world.starting_stage_index, world.options.starting_max_health.value,
                      world.player_name, str(world.multiworld.seed_name))
    patch.write_file(TOKEN_FILE, patch.get_token_binary())


