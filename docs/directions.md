# Direction Notes

This project currently targets the "Reverse-Engineer an Undocumented API"
take-home path.

## Current Scope

The deliverable is an API service over Google Flights private browser RPCs.

Implemented:

- FastAPI service
- Docker setup
- API-owned Google session refresh
- Explore anywhere search
- explicit-destination shopping search branch
- normalized result schema
- structured logs
- regression tests for session/cache/parser behavior

## How To Evaluate

1. Build and run:

   ```bash
   docker compose up --build
   ```

2. Check health:

   ```bash
   curl http://127.0.0.1:8000/healthz
   ```

3. Search anywhere:

   ```bash
   curl -X POST http://127.0.0.1:8000/api/flights/search \
     -H 'content-type: application/json' \
     -d '{"origin":"SFO","outbound_date":"2026-08-01","return_date":"2026-08-08"}'
   ```

4. Search an explicit destination:

   ```bash
   curl -X POST http://127.0.0.1:8000/api/flights/search \
     -H 'content-type: application/json' \
     -d '{"origin":"SFO","destination":"LAX","outbound_date":"2026-08-01","return_date":"2026-08-08"}'
   ```

## Known Limits

- The Google endpoints are private and unstable.
- Booking-provider parsing is planned but not complete.
- The entity cache may need more airports.
- Session refresh requires Playwright Chromium to be installed.

## Submission Notes

Primary docs:

- `README.md`
- `docs/APPROACH.md`
- `docs/DESIGN.md`
- `docs/GOOGLE_FLIGHTS_API_ARCHITECTURE.md`
- `docs/walkthrough.md`
