# Walkthrough

## 1. Start The Full App

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000/
```

The same container serves the React/MUI frontend and FastAPI backend.

If old compose services are reported as orphans:

```bash
docker compose up --build --remove-orphans
```

If an old Google session volume should be cleared:

```bash
docker compose down -v
docker compose up --build
```

## 2. Use The UI

1. Enter a prompt in the chat panel, such as:

   ```text
   surprise me somewhere sunny next week under $1000
   ```

2. Confirm that active filters appear as chips near the toolbar.

3. Open the filter icon to see advanced filters, including stops, max flight
   duration, region, climate, interests, and sort mode.

4. Switch the date mode from `Exact` to `Flexible` when you want the app to scan
   a window for cheaper trips instead of searching one fixed date pair.

5. Review the featured recommendation and destination cards.

## 3. Check Health

```bash
curl http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

## 4. Parse A Travel Prompt

```bash
curl -X POST http://127.0.0.1:8000/api/travel/filters/parse \
  -H 'content-type: application/json' \
  -d '{"message":"sunny next week under $1000","filters":{"origin":"SFO","domestic_international":"any","climates":[],"vibes":[],"sort":"best_match"}}'
```

This returns extracted intent, merged filters, active filter chips, and any
clarifying question.

## 5. Recommend Destinations

```bash
curl -X POST http://127.0.0.1:8000/api/travel/recommend \
  -H 'content-type: application/json' \
  -d '{"message":"places with Japanese temples under $1000","filters":{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08","domestic_international":"any","climates":[],"vibes":[],"sort":"best_match"}}'
```

This runs intent extraction, flight search, weather/places enrichment, ranking,
and recommendation response generation.

## 6. Recommend The Cheapest Flexible-Date Trip

```bash
curl -X POST http://127.0.0.1:8000/api/travel/recommend \
  -H 'content-type: application/json' \
  -d '{"message":"find the cheapest 1 week trip any date in the next 6 months under $1000","filters":{"origin":"SFO","date_mode":"flexible","trip_length_days":7,"flexible_window":"next_6_months","domestic_international":"any","climates":[],"vibes":[],"sort":"cheapest"}}'
```

This generates candidate date pairs inside the selected window, searches each
pair, and ranks the cheapest matching destinations.

## 7. Search Anywhere Directly

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08","include_details":true,"details_limit":10}'
```

The API branches to `GetExploreDestinations`. If `include_details` is true, it
also calls `GetExploreDestinationFlightDetails` for up to `details_limit` rows.

## 8. Search A Specific Destination

```bash
curl -X POST http://127.0.0.1:8000/api/flights/search \
  -H 'content-type: application/json' \
  -d '{"origin":"SFO","destination":"LAX","outbound_date":"2026-08-01","return_date":"2026-08-08"}'
```

The API branches to `GetShoppingResults`.

## 9. Run MCP Server

```bash
python3 -m api.travel.mcp_server
```

MCP tools expose travel intent parsing, flight search, destination exploration,
ranking, and recommendations.

## 10. Watch Logs

Useful log messages:

```text
api.travel.parse.request
api.travel.recommend.request
travel.recommend.search
api.search.request
google_flights.session.cache_hit
google_flights.session.cache_invalid
google_flights.session.refresh_start
google_flights.rpc.start
google_flights.rpc.done
google_flights.search.parsed
google_flights.search.retry_after_failure
```

## 11. Run Tests

```bash
python3 -m unittest discover -v
npm run test --prefix web
npm run build --prefix web
docker build -t flights-anywhere:test .
```
