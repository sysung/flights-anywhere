# Google Flights API Architecture

This project talks to private Google Flights browser RPCs. Playwright is only used
to refresh browser session metadata; normal HTTP requests perform the search,
selection, and booking-result steps.

## Core Idea

Google Flights has two useful funnels:

1. **Explore funnel**: origin plus optional "anywhere" destination.
2. **Shopping funnel**: explicit origin and explicit destination, closer to the
   normal Google Flights booking flow.

Both funnels use the same service path:

```text
/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/{RPC}
```

The shared request envelope is:

```text
POST application/x-www-form-urlencoded
f.req=[null,"<double-serialized request array>"]&at=<optional token>&
```

The shared browser/session metadata is:

- `f.sid`
- `bl`
- `hl`
- cookies and normal browser headers
- optional `at`

## Internal Layers

```text
Client API
  -> Flight workflow service
    -> Session manager
    -> Entity resolver
    -> RPC request builders
    -> RPC transport
    -> RPC response parsers
```

### Session Manager

Responsibilities:

- Load `google_flights_session.json` if it is still usable.
- Refresh with Playwright if the session fails or is missing.
- Save a reusable session template with URL, headers, cookies, and seed `f.req`.

Playwright should only visit Google Flights and capture service requests. It
should not do the whole search workflow unless we are debugging a new RPC shape.

### Entity Resolver

Responsibilities:

- Convert IATA codes into Google entity ids.
- Support special destination `ANYWHERE` as `/m/02j71`.
- Keep actual result airport codes when Google expands an origin to nearby
  airports.

Source:

```text
data/google_flights_entities.json
```

### RPC Transport

Responsibilities:

- Swap the RPC name in the captured URL.
- Strip browser-only or invalid replay headers such as `:authority`,
  `content-length`, `host`, and `accept-encoding`.
- POST encoded `f.req`.
- Decode Google RPC response streams that start with `)]}'`.

## Public API Design

The Explore and Shopping entry points should be merged into one public search
API. The caller supplies the same request shape every time. The backend branches
internally based on whether `destination` is present.

```text
destination omitted/null/"ANYWHERE" -> Explore branch
destination supplied              -> Shopping branch
```

This keeps the frontend and any downstream consumers on a stable schema while
allowing the service to use the best Google RPC for the job.

### `POST /api/flights/search`

Unified search endpoint.

Request:

```json
{
  "origin": "SFO",
  "outbound_date": "2026-08-01",
  "return_date": "2026-08-08",
  "destination": null,
  "nonstop": false,
  "include_details": true,
  "details_limit": 25
}
```

Internal branch:

```text
if destination is null/omitted/ANYWHERE:
  mode = "explore"
  call GetExploreDestinations
  optionally call GetExploreDestinationFlightDetails for route-token details
else:
  mode = "shopping"
  call GetShoppingResults
```

Unified response envelope:

```json
{
  "mode": "explore",
  "selection_stage": "results",
  "query": {
    "origin": "SFO",
    "destination": null,
    "outbound_date": "2026-08-01",
    "return_date": "2026-08-08",
    "nonstop": false,
    "passengers": {
      "adults": 1,
      "children": 0,
      "infants_in_seat": 0,
      "infants_on_lap": 0
    }
  },
  "results": [
    {
      "id": "route-or-option-stable-id",
      "source": "explore",
      "selection_stage": "destination",
      "origin": "SFO",
      "dest": "LAX",
      "outbound_date": "2026-08-01",
      "return_date": "2026-08-08",
      "price": 106,
      "currency": "USD",
      "airline_code": "F9",
      "airline": "Frontier",
      "stops": 0,
      "duration_minutes": 96,
      "flight_num": "F92858",
      "flight_nums": ["F92858"],
      "route_token": "...",
      "option_token": "...",
      "outbound_options": [],
      "return_options": [],
      "booking_options": [],
      "workflow_state": {
        "mode": "explore",
        "search_block": "...",
        "route_token": "..."
      },
      "raw": {
        "rpc": "GetExploreDestinations",
        "path": [0, 0, 2, 1]
      }
    }
  ],
  "workflow_state": {
    "mode": "explore",
    "can_select_outbound": false,
    "can_book": false
  }
}
```

The fields stay stable across both branches:

- `results[]`: normalized rows for display.
- `source`: `explore`, `shopping`, or `booking`.
- `selection_stage`: what the row represents: `destination`, `outbound`,
  `return`, or `booking`.
- `flight_num` and `flight_nums`: exact flight numbers when available.
- `route_token` and `option_token`: private Google tokens needed for follow-up
  calls.
- `outbound_options`, `return_options`, `booking_options`: nested richer data
  when available.
- `workflow_state`: opaque state the frontend returns to selection APIs.
- `raw`: optional parser/debug context. Keep this out of production responses
  unless a debug flag is set.

### Normalization Strategy

The unified schema should preserve information by separating common fields from
branch-specific detail fields.

Common fields available on nearly every row:

```json
{
  "id": "...",
  "source": "explore",
  "selection_stage": "destination",
  "origin": "SFO",
  "dest": "LAX",
  "outbound_date": "2026-08-01",
  "return_date": "2026-08-08",
  "price": 106,
  "currency": "USD",
  "airline_code": "F9",
  "airline": "Frontier",
  "stops": 0,
  "duration_minutes": 96,
  "flight_num": "F92858",
  "flight_nums": ["F92858"]
}
```

Explore-specific fields:

```json
{
  "destination_entity_id": "/m/030qb3t",
  "requested_destination": "ANYWHERE",
  "route_token": "...",
  "result_type": "destination_card",
  "price_is_representative": true
}
```

Shopping-specific fields:

```json
{
  "option_token": "...",
  "fare_brand": "...",
  "departure_time": "...",
  "arrival_time": "...",
  "layovers": [],
  "baggage": {},
  "price_delta": 0
}
```

Booking-specific fields:

```json
{
  "seller": "Frontier",
  "booking_url": "...",
  "raw_token": "...",
  "provider_metadata": {}
}
```

For application code, prefer a Pydantic model with optional fields rather than
separate Explore and Shopping response models. Internally the parser can still
use separate dataclasses for each RPC and convert them into `FlightResult`.

#### Explore Branch

Use this branch when destination is omitted or set to anywhere.

Internal RPCs:

1. `GetExploreDestinations`
2. Optional `GetExploreDestinationFlightDetails` per returned `route_token`

Response:

```json
{
  "mode": "explore",
  "results": [
    {
      "origin": "SFO",
      "dest": "LAX",
      "price": 106,
      "currency": "USD",
      "airline": "Frontier",
      "stops": 0,
      "duration_minutes": 96,
      "route_token": "...",
      "outbound_options": [
        {
          "flight_num": "F92858",
          "flight_nums": ["F92858"],
          "origin": "SFO",
          "dest": "LAX",
          "date": "2026-08-01",
          "price": 106,
          "token": "..."
        }
      ]
    }
  ]
}
```

Use case:

- "Show me everywhere I can go from SFO."
- "Find the cheapest destinations first."

#### Shopping Branch

Use this branch when destination is explicit. This maps to the normal Google
Flights shopping results page.

Request:

```json
{
  "origin": "SFO",
  "destination": "LAX",
  "outbound_date": "2026-07-27",
  "return_date": "2026-07-29",
  "nonstop": false
}
```

Internal RPC:

```text
GetShoppingResults
```

Initial `f.req` shape:

```text
[
  [],
  search_block_with_origin_destination_dates,
  0,
  0,
  0,
  1
]
```

Response uses the same envelope as Explore, but each result is an outbound
flight option instead of a destination card:

```json
{
  "mode": "shopping",
  "selection_stage": "outbound",
  "query": {
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29"
  },
  "results": [
    {
      "id": "outbound-token-or-hash",
      "source": "shopping",
      "selection_stage": "outbound",
      "flight_num": "F92858",
      "flight_nums": ["F92858"],
      "origin": "SFO",
      "dest": "LAX",
      "date": "2026-07-27",
      "outbound_date": "2026-07-27",
      "return_date": "2026-07-29",
      "price": 72,
      "currency": "USD",
      "airline_code": "F9",
      "airline": "Frontier",
      "stops": 0,
      "duration_minutes": 96,
      "route_token": null,
      "option_token": "...",
      "outbound_options": [],
      "return_options": [],
      "booking_options": [],
      "workflow_state": {
        "mode": "shopping",
        "selected_outbound": null,
        "option_token": "..."
      }
    }
  ],
  "workflow_state": {
    "mode": "shopping",
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29",
    "can_select_outbound": true,
    "can_book": false
  }
}
```

Use case:

- "I know I want LAX; show exact flight choices."
- This is preferable to Explore when destination is explicit because it returns
  the bookable shopping flow rather than destination cards.

### `POST /api/flights/select-outbound`

Use this after the user chooses one outbound flight.

Request:

```json
{
  "workflow_state": {
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29"
  },
  "outbound": {
    "token": "...",
    "origin": "SFO",
    "dest": "LAX",
    "date": "2026-07-27",
    "airline_code": "F9",
    "flight_number": "2858"
  }
}
```

Internal RPC:

```text
GetShoppingResults
```

Selected-outbound `f.req` shape:

```text
[
  [null, outbound_token],
  search_block_with_outbound_leg_selected,
  0,
  0,
  0,
  1
]
```

The selected outbound leg is inserted into the outbound leg at index `8`:

```text
[
  ["SFO", "2026-07-27", "LAX", null, "F9", "2858"]
]
```

Response uses the same envelope; `results[]` now contains return options:

```json
{
  "mode": "shopping",
  "selection_stage": "return",
  "query": {
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29"
  },
  "results": [
    {
      "id": "return-token-or-hash",
      "source": "shopping",
      "selection_stage": "return",
      "flight_num": "F94593",
      "flight_nums": ["F94593"],
      "origin": "LAX",
      "dest": "SFO",
      "date": "2026-07-29",
      "price_delta": 0,
      "price": 72,
      "currency": "USD",
      "airline_code": "F9",
      "airline": "Frontier",
      "option_token": "...",
      "outbound_options": [
        {
          "flight_num": "F92858",
          "flight_nums": ["F92858"],
          "origin": "SFO",
          "dest": "LAX",
          "date": "2026-07-27",
          "option_token": "..."
        }
      ],
      "return_options": [],
      "booking_options": [],
      "workflow_state": {
        "mode": "shopping",
        "selected_outbound": {
          "token": "...",
          "airline_code": "F9",
          "flight_number": "2858"
        },
        "return_token": "..."
      }
    }
  ],
  "workflow_state": {
    "mode": "shopping",
    "selected_outbound": {
      "token": "...",
      "airline_code": "F9",
      "flight_number": "2858"
    },
    "can_select_return": true,
    "can_book": false
  }
}
```

Use case:

- "After I pick outbound F92858, show return choices."

### `POST /api/flights/booking-options`

Use this after the user chooses both outbound and return flights.

Request:

```json
{
  "workflow_state": {
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29"
  },
  "outbound": {
    "token": "...",
    "origin": "SFO",
    "dest": "LAX",
    "date": "2026-07-27",
    "airline_code": "F9",
    "flight_number": "2858"
  },
  "return": {
    "token": "...",
    "origin": "LAX",
    "dest": "SFO",
    "date": "2026-07-29",
    "airline_code": "F9",
    "flight_number": "4593"
  }
}
```

Internal RPC:

```text
GetBookingResults
```

Booking `f.req` shape:

```text
[
  [null, return_token],
  search_block_with_both_legs_selected,
  null,
  2
]
```

Both legs carry selected-flight arrays at index `8`:

```text
outbound leg:
[
  ["SFO", "2026-07-27", "LAX", null, "F9", "2858"]
]

return leg:
[
  ["LAX", "2026-07-29", "SFO", null, "F9", "4593"]
]
```

Response uses the same envelope; `results[]` now contains booking providers:

```json
{
  "mode": "booking",
  "selection_stage": "booking",
  "query": {
    "origin": "SFO",
    "destination": "LAX",
    "outbound_date": "2026-07-27",
    "return_date": "2026-07-29"
  },
  "results": [
    {
      "id": "booking-provider-or-hash",
      "source": "booking",
      "selection_stage": "booking",
      "seller": "Frontier",
      "price": 72,
      "currency": "USD",
      "booking_url": "...",
      "raw_token": "...",
      "outbound_options": [
        {
          "flight_num": "F92858",
          "flight_nums": ["F92858"],
          "origin": "SFO",
          "dest": "LAX",
          "date": "2026-07-27"
        }
      ],
      "return_options": [
        {
          "flight_num": "F94593",
          "flight_nums": ["F94593"],
          "origin": "LAX",
          "dest": "SFO",
          "date": "2026-07-29"
        }
      ],
      "booking_options": []
    }
  ],
  "workflow_state": {
    "mode": "booking",
    "can_book": true
  }
}
```

Use case:

- "Show where the selected itinerary can be booked."

## Workflow Selection

### Destination omitted

```text
/api/flights/search
  -> GetExploreDestinations
  -> optional GetExploreDestinationFlightDetails
  -> user picks destination/flight
  -> switch to shopping flow if booking is needed
```

### Destination supplied

```text
/api/flights/search
  -> GetShoppingResults
  -> /api/flights/select-outbound
    -> GetShoppingResults
    -> /api/flights/booking-options
      -> GetBookingResults
```

## Recommended Module Layout

```text
app/google_flights/
  session.py       # Playwright refresh and session JSON storage
  entities.py      # IATA <-> Google entity ids
  transport.py     # RPC URL swapping, headers, POST, response decode
  builders.py      # f.req builders for explore/shopping/booking
  parsers.py       # response parsers into stable app models
  service.py       # orchestration for explore/search/select/book
  models.py        # dataclasses or pydantic request/response models
```

Keep the current script as a CLI/debug harness, but move reusable code into this
package as the API grows.

## Persistence Strategy

Do not persist Google session tokens long-term. Treat them like short-lived
browser credentials.

Good things to persist:

- normalized search results
- selected itinerary state
- entity-id cache
- parser debug samples, with private cookies stripped

Avoid persisting:

- raw cookies
- full captured headers with user/session identifiers
- `at` tokens
- full booking responses if they contain user/session specific checkout data

## Open Parser Work

The current Explore implementation already parses:

- destination cards from `GetExploreDestinations`
- route-token outbound options from `GetExploreDestinationFlightDetails`

Next parser work:

1. Parse initial `GetShoppingResults` outbound options.
2. Parse selected-outbound `GetShoppingResults` return options.
3. Parse `GetBookingResults` booking providers, prices, and deep links.
4. Normalize all tokens into an app-level `workflow_state` so clients do not
   need to understand Google RPC internals.
