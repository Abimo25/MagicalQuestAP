# ====================
# = In-game messages =
# ====================
# Pure logic for the item messages that the patch draws near the bottom of the screen (no SNI here, so the
# tests can drive it directly). The client builds a Message for each received, found or sent Item, queues it, and
# writes the next one into AP RAM when the ROM is idle.
#
# Font: A-Z at their ASCII codes, 0-9 at $00-$09, space $20, punctuation at $10-$1F.
# Nothing is shown on the World Map (its text rows hold the Level Select):
# messages wait for the next Level, the jingles still play.

import unicodedata
from collections import deque
from typing import Deque, Iterable, List, NamedTuple, Optional

from . import Ram

LINE_MAX = 60                         # characters per line the ROM accepts (it scrolls anything over 30)
SUMMARY_THRESHOLD = 3                 # more than this many waiting -> summaries
END_OF_LINE = 0xFF
UNKNOWN_TILE = 0x1D                   # "×" special character for missing symbols.
SPACE_TILE = 0x20

PUNCTUATION = {"$": 0x11, "'": 0x13, "!": 0x14, "?": 0x15, ";": 0x16, ":": 0x17, ",": 0x18, ".": 0x19,
               '"': 0x1A, "(": 0x1B, ")": 0x1C, "-": 0x1E, "=": 0x1F, " ": SPACE_TILE}

# Archipelago item classification flags (BaseClasses.ItemClassification)
FLAG_PROGRESSION, FLAG_USEFUL, FLAG_TRAP = 0b001, 0b010, 0b100

# Importance for colours and summaries: progression > trap > useful > filler
RANK_FILLER, RANK_USEFUL, RANK_TRAP, RANK_PROGRESSION = 0, 1, 2, 3
RANK_ATTR = {RANK_PROGRESSION: Ram.ATTR_PROGRESSION, RANK_TRAP: Ram.ATTR_TRAP,
             RANK_USEFUL: Ram.ATTR_USEFUL, RANK_FILLER: Ram.ATTR_FILLER}

RECEIVED, FOUND, SENT, SUMMARY = "received", "found", "sent", "summary"
MODES = ("all", "received", "off")    # all: received, found and sent; received: no sent; off: nothing


def rank(flags: int) -> int:
    if flags & FLAG_PROGRESSION:
        return RANK_PROGRESSION
    if flags & FLAG_TRAP:
        return RANK_TRAP
    if flags & FLAG_USEFUL:
        return RANK_USEFUL
    return RANK_FILLER


class Message(NamedTuple):
    kind: str                 # RECEIVED, FOUND, SENT or SUMMARY
    line1: str
    line2: str
    rank: int

    @property
    def attr(self) -> int:
        return RANK_ATTR[self.rank]


def received(item: str, sender: str, flags: int) -> Message:
    return Message(RECEIVED, f"RECEIVED {item}", f"FROM {sender}", rank(flags))


def found(item: str, flags: int) -> Message:
    return Message(FOUND, f"FOUND {item}", "", rank(flags))


def sent(item: str, receiver: str, flags: int) -> Message:
    return Message(SENT, f"SENT {item}", f"TO {receiver}", rank(flags))


def allowed(message: Message, mode: str) -> bool:
    if mode == "off":
        return False
    return mode == "all" or message.kind != SENT


# ---- Text to tiles ---------------------------------------------------------------------------------------------
def normalize(text: str) -> str:
    # Accents off (á -> A, Ó -> O), uppercase.
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).upper()


def char_tile(c: str) -> int:
    if "A" <= c <= "Z":
        return ord(c)
    if "0" <= c <= "9":
        return ord(c) - ord("0")
    return PUNCTUATION.get(c, UNKNOWN_TILE)


def line_tiles(text: str) -> bytes:
    # Up to LINE_MAX tiles; END_OF_LINE fills the rest so the ROM knows the length.
    tiles = bytes(char_tile(c) for c in normalize(text)[:LINE_MAX])
    return tiles + bytes([END_OF_LINE] * (LINE_MAX - len(tiles)))


# ---- Queue -----------------------------------------------------------------------------------------------------
def summarize(messages: Iterable[Message]) -> List[Message]:
    # At most two summaries: everything received or found, everything sent; each in the colour of its best item.
    got = [m for m in messages if m.kind in (RECEIVED, FOUND, SUMMARY) and not m.line1.startswith("SENT")]
    gave = [m for m in messages if m not in got]
    out = []
    for group, verb in ((got, "RECEIVED"), (gave, "SENT")):
        if group:
            count = sum(summary_count(m) for m in group)
            out.append(Message(SUMMARY, f"{verb} {count} ITEMS", "", max(m.rank for m in group)))
    return out


def summary_count(message: Message) -> int:
    if message.kind == SUMMARY:
        return int(message.line1.split()[1])
    return 1


class MessageQueue:
    def __init__(self) -> None:
        self.waiting: Deque[Message] = deque()

    def __len__(self) -> int:
        return len(self.waiting)

    def push(self, message: Message) -> None:
        self.waiting.append(message)

    def clear(self) -> None:
        self.waiting.clear()

    def next(self) -> Optional[Message]:
        # Summaries when more than SUMMARY_THRESHOLD wait, then first in, first out.
        if len(self.waiting) > SUMMARY_THRESHOLD:
            self.waiting = deque(summarize(self.waiting))
        return self.waiting.popleft() if self.waiting else None





