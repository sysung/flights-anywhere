# Flights Anywhere

AI-powered destination discovery on top of reverse-engineered Google Flights
browser RPCs. The app combines a React/MUI travel UI, FastAPI endpoints, an MCP
server, Gemini intent extraction, and deterministic flight ranking.

## What This Does

- Runs the frontend and backend together with `docker compose up --build`.
- Lets users ask natural-language travel prompts such as "surprise me" or
  "sunny next week under $1000."
- Converts chat into structured filters, active chips, clarifying questions, and
  ranked destination recommendations.
- Keeps real flight data as the source of truth for prices, durations, stops,
  route tokens, and availability.
- Supports flexible-date cheapest-trip discovery across generated date pairs in
  the next month, next three months, or next six months.
- Adds swappable weather and places enrichment providers for prompts like
  "sunny next week" or "Japanese temples."
- Exposes the same recommendation logic through REST endpoints and MCP tools.
- Supports direct flight search with one unified API contract:
  - no destination: Explore / anywhere search
  - destination supplied: Shopping / explicit route search
- Normalizes results into one schema with prices, route tokens, option tokens,
  flight numbers when available, durations, stops, and workflow state.

## Setup

For Docker-only usage, create `.env` from `.env.example` and then skip straight
to `docker compose up --build`.

For local Python development:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

`pip install -r requirements.txt` installs the Playwright Python package.
`python3 -m playwright install chromium` installs the browser binary Playwright
drives. Docker runs both steps automatically during image build.

For local frontend development:

```bash
cd web
npm install
```

## Run The App

Run the full app with Docker:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000/
```

The Docker image builds the React/MUI frontend and serves it from FastAPI, so the
UI and API run together from the same container. API routes remain available
under `/api`, for example `http://localhost:8000/api/flights/search`.

For local backend-only development:

```bash
uvicorn api.main:app --reload
```

For local frontend-only development:

```bash
cd web
npm install
npm run dev
```

Vite proxies `/api` requests to `http://127.0.0.1:8000`.

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

Session capture defaults to a 45-second timeout. Override it when debugging slow
local or Railway browser startup:

```bash
GOOGLE_FLIGHTS_SESSION_CAPTURE_TIMEOUT_SECONDS=30
```

Fresh Google Travel sessions may ask for an origin before emitting the Flights
RPC this API needs. The session bootstrap uses `SFO` by default only to capture a
valid request template; user searches still use the origin in the API request.

```bash
GOOGLE_FLIGHTS_SESSION_BOOTSTRAP_ORIGIN=SFO
```

Set log verbosity with:

```bash
LOG_LEVEL=INFO uvicorn api.main:app --reload
```

Set Gemini configuration with:

```bash
GOOGLE_CLOUD_API_KEY=xxxxx
GEMINI_MODEL=gemini-3.5-flash
```

Useful log events include:

- `api.travel.parse.request`
- `api.travel.recommend.request`
- `travel.recommend.search`
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

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Parse a travel prompt into filters:

```bash
curl -X POST http://127.0.0.1:8000/api/travel/filters/parse \
  -H 'content-type: application/json' \
  -d '{"message":"sunny next week under $1000","filters":{"origin":"SFO","domestic_international":"any","climates":[],"vibes":[],"sort":"best_match"}}'
```

Ask for AI destination recommendations:

```bash
curl -X POST http://127.0.0.1:8000/api/travel/recommend \
  -H 'content-type: application/json' \
  -d '{"message":"surprise me somewhere sunny next week under $1000","filters":{"origin":"SFO","domestic_international":"any","climates":[],"vibes":[],"sort":"best_match"}}'
```

Ask for the cheapest flexible-date trip:

```bash
curl -X POST http://127.0.0.1:8000/api/travel/recommend \
  -H 'content-type: application/json' \
  -d '{"message":"find the cheapest 1 week trip any date in the next 6 months under $1000","filters":{"origin":"SFO","date_mode":"flexible","trip_length_days":7,"flexible_window":"next_6_months","domestic_international":"any","climates":[],"vibes":[],"sort":"cheapest"}}'
```

Flexible date mode uses `date_mode: "flexible"`, a `trip_length_days` value, and
`flexible_window` set to `next_month`, `next_3_months`, or `next_6_months`. The
recommendation service expands that into candidate outbound/return date pairs,
searches Google Flights for each pair, and keeps the cheapest result per
destination before ranking.

## MCP Server

Run the stdio MCP server with:

```bash
python3 -m api.travel.mcp_server
```

It exposes tools for parsing travel intent, searching flights, exploring
destinations, ranking destinations, and generating destination recommendations.

## CI/CD And Railway Deployment

GitHub Actions runs tests and deploys to Railway on pushes to `main`. Runtime
secrets stay in GitHub, and the CD workflow syncs them into Railway service
variables immediately before running `railway up`.

The Railway service uses the Dockerfile builder. The Docker image builds the
Vite frontend, installs Python dependencies, installs Playwright Chromium with
system dependencies, and serves the frontend and API from FastAPI.

Use these Railway settings:

- **Builder:** `Dockerfile`
- **Custom Build Command:** leave blank
- **Custom Start Command:** leave blank, or use
  `sh -c 'uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}'`
- **Healthcheck Path:** `/healthz`

Required Railway variables:

```text
ENVIRONMENT=production
LOG_LEVEL=INFO
GOOGLE_CLOUD_API_KEY=xxxxx
GEMINI_MODEL=gemini-3.5-flash
GOOGLE_FLIGHTS_SESSION_PATH=/app/api/.session/google_flights_session.json
GOOGLE_FLIGHTS_SESSION_TTL_SECONDS=3600
GOOGLE_FLIGHTS_SESSION_CAPTURE_TIMEOUT_SECONDS=45
GOOGLE_FLIGHTS_SESSION_BOOTSTRAP_ORIGIN=SFO
```

If the Railway UI is currently set to `Railpack`, switch it to `Dockerfile`.
Railpack can build simple Python/Node apps, but Dockerfile is safer here because
Playwright Chromium needs browser and OS dependencies.

Required GitHub Actions secrets:

```text
RAILWAY_TOKEN
GOOGLE_CLOUD_API_KEY
```

Recommended GitHub Actions variables:

```text
RAILWAY_SERVICE=flights-anywhere
RAILWAY_ENVIRONMENT=production
RAILWAY_PROJECT_ID=<your Railway project id, if the repo is not linked>
RAILWAY_PUBLIC_URL=https://your-app.up.railway.app
GEMINI_MODEL=gemini-3.5-flash
GOOGLE_FLIGHTS_SESSION_CAPTURE_TIMEOUT_SECONDS=45
GOOGLE_FLIGHTS_SESSION_BOOTSTRAP_ORIGIN=SFO
```

`RAILWAY_PUBLIC_URL` is optional, but when present the CD workflow runs a
post-deploy smoke test against `/healthz`.

## Debugging

Use the API and structured logs for debugging. The service refreshes its own
session automatically, retries once after Google RPC failures, and logs the
search and details workflow so you can inspect what happened without running
standalone helper scripts.

## Tests

Backend:

```bash
python3 -m unittest discover -v
```

Frontend:

```bash
npm run test --prefix web
npm run build --prefix web
```

Docker:

```bash
docker build -t flights-anywhere:test .
```

Current coverage includes:

- entity resolution
- `f.req` encode/decode
- stable seed request shape
- session TTL, corrupt cache, and malformed cache refresh
- request-builder mutation for Explore and Shopping
- Explore result parsing
- exact flight-number parsing
- parser dedupe and unknown-shape handling
- mocked Explore and Shopping service flows
- retry after Google HTTP failures
- API error mapping and health endpoint
- travel intent parsing and filter merging
- weather/places-aware recommendation ranking
- flexible-date cheapest-trip search and ranking
- MCP tool wrapper smoke tests
- frontend filter drawer, chat, card, loading, and error flows
- Playwright E2E coverage for loading, timeout, and sunny-under-budget discovery

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
  travel/
    enrichment.py                 # weather/places provider abstractions
    intent.py                     # Gemini + heuristic intent extraction
    mcp_server.py                 # stdio MCP tools
    models.py                     # travel recommendation schemas
    service.py                    # recommendation orchestration/ranking
data/google_flights_entities.json # known IATA/entity mappings
docs/APPROACH.md
docs/directions.md
docs/walkthrough.md
docs/video.md
tests/
web/                              # Vite React + MUI frontend
```

## Notes

These are private Google browser RPCs, not an official API. Payload shapes,
tokens, cookies, and response structures can change without notice. Keep raw
session data out of git and expect to refresh sessions periodically.
