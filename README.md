# Flights Anywhere

Live URL: https://flights-anywhere-production.up.railway.app

AI-powered destination discovery on top of reverse-engineered Google Flights
browser RPCs. The app combines a React/MUI travel UI, FastAPI REST endpoints, a
Streamable HTTP MCP endpoint, Gemini intent extraction, deterministic ranking,
close-match recovery when a search is over-constrained, and verified fallback
suggestions when the app needs to relax filters further.

## What This Does

### Supports Natural-Language Travel Planning

You can start with a real thought instead of a rigid form. Ask for something
like "somewhere sunny next week under $1000" or "surprise me with a quick
international trip," and the app turns that into useful travel filters and
recommendations without making you translate your idea into airline search
syntax first.

### Helps You Discover Destinations You Would Not Have Searched For

Flights Anywhere is built for people who know the kind of trip they want before
they know the destination. Instead of forcing an exact city upfront, it can
surface and rank options that match your budget, timing, vibe, and travel
preferences so discovery feels inspiring rather than overwhelming.

### Finds Better Options Across Dates, Budget, and Convenience

The app can look beyond one exact departure and return date to help you spot
cheaper or better-fitting trips. That means you can compare options based on
what matters to you most, like lower prices, shorter flights, nonstop routes,
or flexible timing, without manually repeating the same search over and over.

### Grounds Recommendations In Real Flight Options

Suggestions are not just generic travel ideas. The app ties recommendations back
to actual flight availability, prices, durations, and stops, so when it tells
you a destination is a strong match, there is a real itinerary behind that
recommendation.

### Makes Travel Search Feel More Guided

If your request is missing something important, like an origin or usable date
range, the app asks a focused follow-up instead of failing silently. That makes
the experience feel closer to planning with a helpful assistant and less like
wrestling with a complicated booking tool.

### Returns Close Matches Instead Of Dead Ends

When no destination satisfies every active filter exactly, the app does not
shut the traveler down with an empty page. It can surface broader close matches
first, explain that they are near-fits rather than perfect fits, and still keep
verified fallback options in reserve when it needs to relax filters further.

### Keeps Search Controls Compact And Easy To Scan

The main trip controls stay inline across the top so travelers can adjust
origin, destination, dates, and budget without hunting through another panel.
Any active choice stays visible as a pill afterward, which makes it easy to see
what is shaping the results at a glance.

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

The Docker image builds the React/MUI frontend and serves it from FastAPI, so
the UI, REST API, and Streamable HTTP MCP endpoint run from the same container.
API routes remain available under `/api`, and MCP is mounted at `/mcp`.

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
recommendation service samples a small set of candidate outbound/return date
pairs across that window, searches Google Flights for each pair, and keeps the
cheapest result per destination before ranking.

Use existing filters without adding new chat intent:

```bash
curl -X POST http://127.0.0.1:8000/api/travel/recommend \
  -H 'content-type: application/json' \
  -d '{"message":"find trips that match my filters","filters":{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08","budget_max":1000}}'
```

## MCP Server

The all-in-one FastAPI process serves MCP over Streamable HTTP alongside the UI
and REST API:

```text
http://localhost:8000/mcp
```

`/mcp` redirects to `/mcp/`, which is the session-oriented Streamable HTTP
endpoint used by the integration tests and MCP clients.

The Railway endpoint is:

```text
https://flights-anywhere-production.up.railway.app/mcp
```

REST and MCP share the same `GoogleFlightsService` and
`TravelRecommendationService` instances.

The stdio transport remains available for clients that spawn a local MCP child
process:

```bash
python3 -m api.travel.mcp_server
```

It exposes tools for parsing travel intent, searching flights, exploring
destinations, ranking destinations, and generating destination recommendations.
The HTTP and stdio transports publish the same tool set.

## CI/CD And Railway Deployment

GitHub Actions runs tests and deploys to Railway on pushes to `main`. Runtime
secrets stay in GitHub, and the CD workflow syncs them into Railway service
variables immediately before running `railway up`. When `RAILWAY_PUBLIC_URL` is
set, the workflow also smoke-tests both `/healthz` and the deployed MCP
endpoint.

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
post-deploy smoke test against `/healthz` and performs an MCP initialize,
tool-list, and intent-parsing handshake against `/mcp`.

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

Running Compose MCP smoke test:

```bash
docker compose up -d --build
MCP_SMOKE_URL=http://localhost:8000/mcp \
  python3 -m unittest tests.test_mcp_smoke -v
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
- relaxed close-match recommendations plus verified fallback generation and reuse
- flexible-date cheapest-trip search and ranking
- MCP initialization, tool discovery, all-tool execution, error recovery,
  session isolation, route coexistence, and external deployment smoke tests
- frontend inline-filter, chat, card, loading, and error flows
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
    mcp_server.py                 # Streamable HTTP and stdio MCP tools
    models.py                     # travel recommendation schemas
    service.py                    # recommendation orchestration/ranking
data/google_flights_entities.json # known IATA/entity mappings
docs/APPROACH.md
docs/directions.md
docs/video.md
tests/
web/                              # Vite React + MUI frontend
```

## Notes

These are private Google browser RPCs, not an official API. Payload shapes,
tokens, cookies, and response structures can change without notice. Keep raw
session data out of git and expect to refresh sessions periodically.
