# Design

## API Shape

The public API is intentionally small:

```text
GET  /healthz
POST /api/flights/search
```

`POST /api/flights/search` accepts:

```json
{
  "origin": "SFO",
  "destination": "LAX",
  "outbound_date": "2026-08-01",
  "return_date": "2026-08-08",
  "nonstop": false,
  "include_details": true,
  "details_limit": 10
}
```

`destination` is optional. When omitted, the service searches Google Flights
Explore anywhere results. When supplied, it uses the Shopping workflow for an
explicit route.

## Response Envelope

Both branches return the same top-level structure:

```json
{
  "mode": "explore",
  "selection_stage": "results",
  "query": {},
  "results": [],
  "workflow_state": {}
}
```

Each result uses one normalized model with optional fields:

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
  "flight_nums": ["F92858"],
  "route_token": "...",
  "option_token": "...",
  "outbound_options": [],
  "return_options": [],
  "booking_options": [],
  "workflow_state": {}
}
```

## Module Layout

```text
api/
  main.py                         # FastAPI routes
  google_flights/
    builders.py                   # f.req builders
    codec.py                      # f.req and RPC response decoding
    constants.py                  # RPC names, paths, defaults
    entities.py                   # IATA -> Google entity resolver
    models.py                     # Pydantic schemas
    parsers.py                    # response parsers
    service.py                    # workflow orchestration
    session.py                    # Playwright session capture/cache/refresh
    transport.py                  # HTTP RPC transport
```

## Session Design

The API owns its Google session state:

```text
api/.session/google_flights_session.json
```

The file is ignored by git. It contains cookies and request metadata, so it
should be treated like a short-lived secret.

Session behavior:

- load from memory if present and fresh
- load from file if present, fresh, and structurally valid
- refresh with Playwright if missing, stale, malformed, or after a Google RPC
  failure
- refresh every hour by default

Important detail: the API does **not** persist Google's captured `f.req`
verbatim. It keeps fresh session metadata but writes a stable seed `f.req` so the
builders always receive the mutable round-trip leg shape they expect.

## Logging

The service emits readable operational logs:

- `api.search.request`
- `api.search.response`
- `google_flights.session.cache_hit`
- `google_flights.session.cache_invalid`
- `google_flights.session.refresh_start`
- `google_flights.session.refresh_done`
- `google_flights.rpc.start`
- `google_flights.rpc.done`
- `google_flights.search.start`
- `google_flights.search.parsed`
- `google_flights.search.retry_after_failure`
- `google_flights.details.parsed`

Use:

```bash
LOG_LEVEL=INFO uvicorn api.main:app --reload
```

## Error Handling

- bad user input maps to HTTP 400
- session/browser/Google RPC availability failures map to HTTP 503
- unexpected failures map to HTTP 500 with stack traces in server logs

The service retries once with a fresh session after session-shape failures and
Google HTTP failures.
