# ================
# = Access Rules =
# ================
#  Parses the rule strings of data/gates_data.py and sets them on entrances, Locations and the goal.
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional

from rule_builder.rules import Has, Rule

from .data import gates_data as gates
from .data import locations_data as locations
from .names import item_name as I
from .names import location_name as L
from .names import region_name as R
from .Regions import entrance_name

if TYPE_CHECKING:
    from . import MagicalQuestWorld

_TOKEN = re.compile(r"\s*([A-Z]+|[()&|])")


def parse_rule(expression: str) -> Optional[Rule]:
    # Rule for an expression of W, F, M, COINS, EMBLEMS, &, | and parentheses ('&' binds tighter). "" gives None (no requirement).
    tokens: List[str] = []
    position = 0
    text = expression.strip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            raise ValueError(f"bad rule {expression!r} at {position}")
        tokens.append(match.group(1))
        position = match.end()
    if not tokens:
        return None
    index = 0

    def peek() -> Optional[str]:
        return tokens[index] if index < len(tokens) else None

    def take() -> str:
        nonlocal index
        index += 1
        return tokens[index - 1]

    def or_expression() -> Rule:
        rule = and_expression()
        while peek() == "|":
            take()
            rule = rule | and_expression()
        return rule

    def and_expression() -> Rule:
        rule = factor()
        while peek() == "&":
            take()
            rule = rule & factor()
        return rule

    def factor() -> Rule:
        token = take() if peek() is not None else ""
        if token == "(":
            rule = or_expression()
            if peek() != ")":
                raise ValueError(f"missing ')' in rule {expression!r}")
            take()
            return rule
        if token not in gates.TOKENS:
            raise ValueError(f"unknown token {token!r} in rule {expression!r}")
        count = gates.EMBLEMS_REQUIRED if token == "EMBLEMS" else 1
        return Has(gates.TOKENS[token], count=count)

    rule = or_expression()
    if index != len(tokens):
        raise ValueError(f"unexpected {tokens[index]!r} in rule {expression!r}")
    return rule


def _set(world: MagicalQuestWorld, spot, expression: str) -> None:
    rule = parse_rule(expression)
    if rule is not None:
        world.set_rule(spot, rule)


def set_all_rules(world: MagicalQuestWorld) -> None:
    set_entrance_rules(world)
    set_location_rules(world)
    world.set_completion_rule(Has(I.victory))


def set_entrance_rules(world: MagicalQuestWorld) -> None:
    for stage, fragment in gates.STAGE_ENTRY.items():
        world.set_rule(world.get_entrance(entrance_name(R.menu, stage)), Has(fragment))
    for source, target, expression in gates.LEVEL_EXITS:
        _set(world, world.get_entrance(entrance_name(source, target)), expression)
    for level, store, expression in gates.STORE_DOORS:
        _set(world, world.get_entrance(entrance_name(level, store)), expression)


def set_location_rules(world: MagicalQuestWorld) -> None:
    for loc in locations.LOCATIONS:
        _set(world, world.get_location(loc.name), loc.rule)
    _set(world, world.get_location(L.emperor_pete_event), locations.EVENT_RULE)


