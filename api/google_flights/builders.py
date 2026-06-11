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
        for leg_index, side in ((0, 0), (0, 1), (1, 0), (1, 1)):
            if len(legs[leg_index][side][0][0]) < 2:
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
        legs[leg_index][side][0][0][0] = entity_id
        legs[leg_index][side][0][0][1] = entity_type
    legs[0][6] = query.outbound_date
    legs[1][6] = query.return_date
    if query.nonstop is not None:
        for leg in legs:
            leg[3] = 1 if query.nonstop else 0
