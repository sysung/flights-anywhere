from __future__ import annotations

import copy
from typing import Any

from api.google_flights.codec import encode_inner, search_block
from api.google_flights.entities import Place


def explore_request(inner: list[Any], form: dict[str, str], query: Any, origin: Place, dest: Place) -> str:
    block = copy.deepcopy(search_block(inner))
    _set_legs(block, query, origin, dest)
    return encode_inner([[], None, None, block, None, 1, None, 0, None, 0, [1281, 521], 2], form)


def shopping_request(inner: list[Any], form: dict[str, str], query: Any, origin: Place, dest: Place) -> str:
    block = copy.deepcopy(search_block(inner))
    _set_legs(block, query, origin, dest)
    return encode_inner([[], block, 0, 0, 0, 1], form)


def explore_details_request(
    inner: list[Any],
    form: dict[str, str],
    query: Any,
    origin: Place,
    dest: Place,
    route_token: str,
) -> str:
    block = copy.deepcopy(search_block(inner))
    _set_legs(block, query, origin, dest)
    if len(block) <= 26:
        block.extend([None] * (27 - len(block)))
    block[26] = [dest.entity_id, dest.type or 4]
    return encode_inner([[None, route_token], block], form)


def _set_legs(block: list[Any], query: Any, origin: Place, dest: Place) -> None:
    try:
        legs = block[13]
        if len(legs) < 2:
            raise IndexError
        for leg in legs[:2]:
            if len(leg) < 2:
                raise IndexError
    except (IndexError, TypeError) as exc:
        raise ValueError("Google Flights session f.req has an unsupported leg shape; refresh the session.") from exc

    origin_type = origin.type or 4
    dest_type = dest.type or 4
    values = [
        (0, 0, origin.entity_id, origin_type),
        (0, 1, dest.entity_id, dest_type),
        (1, 0, dest.entity_id, dest_type),
        (1, 1, origin.entity_id, origin_type),
    ]
    for leg_index, side, entity_id, entity_type in values:
        _set_place(legs[leg_index], side, entity_id, entity_type)
    _set_date(legs[0], query.outbound_date)
    _set_date(legs[1], query.return_date)
    if query.nonstop is not None:
        for leg in legs:
            leg[3] = 1 if query.nonstop else 0


def _set_place(leg: list[Any], side: int, entity_id: str, entity_type: int) -> None:
    if len(leg) <= side:
        leg.extend([] for _ in range(side + 1 - len(leg)))
    if not leg[side]:
        leg[side] = [[[None, None]]]
    leg[side][0][0][0] = entity_id
    leg[side][0][0][1] = entity_type


def _set_date(leg: list[Any], value: str) -> None:
    if len(leg) <= 6:
        leg.extend([None] * (7 - len(leg)))
    leg[6] = value
