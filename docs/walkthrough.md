# Walkthrough

## 1. Start The Service

Local:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
uvicorn api.main:app --reload
```

Docker:

```bash
docker compose up --build
```

If old compose services are reported as orphans:

```bash
docker compose up --build --remove-orphans
```

If an old session volume should be cleared:

```bash
docker compose down -v
docker compose up --build
```

## 2. Check Health

```bash
curl http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

## 3. Search Anywhere

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08","include_details":true,"details_limit":10}'
```

The API branches to `GetExploreDestinations`. If `include_details` is true, it
also calls `GetExploreDestinationFlightDetails` for up to `details_limit` rows.

## 4. Search A Specific Destination

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","destination":"LAX","outbound_date":"2026-08-01","return_date":"2026-08-08"}'
```

The API branches to `GetShoppingResults`.

## 5. Watch Logs

Useful log messages:

```text
api.search.request
google_flights.session.cache_hit
google_flights.session.cache_invalid
google_flights.session.refresh_start
google_flights.rpc.start
google_flights.rpc.done
google_flights.search.parsed
google_flights.search.retry_after_failure
```

## 6. Run Tests

```bash
python3 -m unittest discover -v
```
