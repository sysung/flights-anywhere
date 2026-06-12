# Video Walkthrough

Add the walkthrough link here before submission.

Suggested demo flow:

1. Start the all-in-one app:

   ```bash
   docker compose up --build
   ```

2. Open `http://localhost:8000/` and show the React/MUI destination discovery
   UI.

3. Ask the chat:

   ```text
   surprise me somewhere sunny next week under $1000
   ```

4. Ask for the cheapest flexible-date version:

   ```text
   find the cheapest 1 week trip any date in the next 6 months under $1000
   ```

5. Show active filter chips, the flexible date toolbar controls, the filter
   drawer, the featured recommendation, and destination cards.

6. Call `GET /healthz`.

7. Call `POST /api/travel/filters/parse`.

8. Call `POST /api/travel/recommend`.

9. Call `POST /api/flights/search` without a destination.

10. Call `POST /api/flights/search` with `destination: "LAX"`.

11. Show logs for session refresh, Google RPC calls, and recommendation flow.

12. Run:

   ```bash
   python3 -m unittest discover -v
   npm run test --prefix web
   npm run build --prefix web
   ```
