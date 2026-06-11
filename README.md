# Google Flights RPC API

Reverse-engineered Google Flights API helpers for Explore, Shopping, and booking
workflow research. Playwright is used only to refresh browser session metadata;
normal HTTP requests perform the search calls.

## What This Does

- Captures a reusable Google Flights browser session template.
- Searches Google Flights with one unified API contract.
- Uses destination presence to choose the workflow:
  - no destination: Explore / anywhere search
  - destination supplied: Shopping / explicit route search
- Normalizes results into one schema with prices, route tokens, option tokens,
  flight numbers when available, durations, stops, and workflow state.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

`pip install -r requirements.txt` installs the Playwright Python package.
`python3 -m playwright install chromium` installs the browser binary Playwright
drives. Docker runs both steps automatically during image build.

## Run The API

Start locally:

```bash
uvicorn api.main:app --reload
```

Or with Docker:

```bash
docker compose up --build
```

If Docker reports old services as orphans after the project was simplified, clean
them up with:

```bash
docker compose up --build --remove-orphans
```

If you previously ran a version that cached a malformed session, rebuild and let
the API refresh it automatically. To force a completely clean session volume:

```bash
docker compose down -v
docker compose up --build
```

The API manages its own Google Flights session at `api/.session/`. It refreshes
the session when missing, when older than one hour, or after a failed Google RPC
request. The session file contains browser cookies and request metadata, so it is
ignored by git.

Set log verbosity with:

```bash
LOG_LEVEL=INFO uvicorn api.main:app --reload
```

Useful log events include:

- `google_flights.session.cache_hit`
- `google_flights.session.refresh_start`
- `google_flights.rpc.start`
- `google_flights.rpc.done`
- `google_flights.search.parsed`
- `google_flights.details.parsed`
- `google_flights.search.retry_after_failure`

Search anywhere:

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08","include_details":true,"details_limit":10}'
```

Search an explicit destination:

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","destination":"LAX","outbound_date":"2026-08-01","return_date":"2026-08-08"}'
```

## CLI Debugging

The original CLI remains useful for inspecting raw responses. If you want to use
it directly, create a standalone session file first:

```bash
python3 scripts/capture_google_flights_session.py --headless --auto-search --out google_flights_session.json
```

Then run:

```bash
python3 scripts/google_flights_explore.py google_flights_session.json \
  --origin SFO \
  --outbound-date 2026-08-01 \
  --return-date 2026-08-08 \
  --send \
  --include-details \
  --details-limit 25 \
  --json-out flights.json
```

## Tests

```bash
python3 -m unittest discover -v
```

Current coverage includes:

- entity resolution
- `f.req` encode/decode
- Explore result parsing
- exact flight-number parsing
- mocked Explore and Shopping service flows
- FastAPI route schema test, skipped if FastAPI is not installed

## Project Layout

```text
api/
  main.py                         # FastAPI endpoint
  google_flights/
    builders.py                   # f.req builders
    codec.py                      # RPC and f.req decoding
    entities.py                   # IATA -> Google entity ids
    models.py                     # API schemas
    parsers.py                    # response parsers
    service.py                    # workflow orchestration
    session.py                    # session capture/cache/refresh
    transport.py                  # HTTP RPC transport
data/google_flights_entities.json # known IATA/entity mappings
docs/GOOGLE_FLIGHTS_API_ARCHITECTURE.md
scripts/
tests/
```

## Notes

These are private Google browser RPCs, not an official API. Payload shapes,
tokens, cookies, and response structures can change without notice. Keep raw
session data out of git and expect to refresh sessions periodically.
