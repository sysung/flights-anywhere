# Approach: SFO Anywhere Flights

## 🎯 Problem & Choice
I chose to build a **Reverse-Engineered Flight Discovery Engine** (Problem 1) combined with a **Mini-App Assistant** (Problem 2). 

Traditional flight APIs (Amadeus, Skyscanner) are often paywalled, return stale data in sandboxes, or have rigid schemas that don't support "anywhere" discovery well. Google Flights is the gold standard for speed and depth, but it is notoriously difficult to scrape because it uses:
1. **Wiz Binary Streams**: Data is streamed in chunks via XHR/Fetch using a proprietary Google "Wiz" format containing nested, double-serialized JSON and base64-encoded Protobuf payloads.
2. **Aggressive Anti-Bot**: Dynamic selectors and rate-limiting.

I built a solution that intercepts these Wiz streams at the browser level using Playwright, decodes the Protobuf payloads on the fly, and presents a modern dashboard with a Gemini-powered "agentic" assistant.

## 🏗️ Technical Implementation

### 1. The Scraper (The "Hard Part")
- **Wiz Stream Interception**: Instead of parsing the DOM (which is brittle), I injected a Javascript hook into the Playwright browser context to intercept all `XMLHttpRequest` and `fetch` calls.
- **Protobuf Decoding**: I used `blackboxprotobuf` to dynamically decode the base64-encoded messages found inside the Wiz stream. This allowed me to extract clean pricing and flight data directly from the binary source.
- **Dynamic Airport Seeding**: The system automatically detects new airport codes in the stream and can be extended to seed a comprehensive airport database.

### 2. The AI Integration
- **Natural Language Sync**: The AI assistant (Gemini 3.5 Flash) doesn't just "chat." It acts as a controller. When a user asks "Show me flights to London under $800," the agent extracts structured JSON filters (`max_price`, `destination`, `airlines`).
- **Real-time Filtering**: The frontend synchronizes these AI-extracted filters with the UI components (Sliders, Autocomplete) in real-time, instantly updating the DataGrid results.

### 3. Architecture & Refactoring
- **Modular Backend**: Reorganized the codebase into `core` (logic), `db` (storage), and `scraper` (ingestion) modules for clean separation of concerns.
- **Root Delegation**: Added a root `package.json` to allow one-command build/dev workflows from the workspace root.
- **PostgreSQL**: Used for reliable, indexed storage of flight listings and scraper logs.

## 🛠️ Decisions & Tradeoffs
- **Vanilla CSS vs Tailwind**: I preferred **Vanilla CSS** within MUI's `sx` prop for maximum control over the "Google Flights" aesthetic without adding the overhead of a large CSS utility framework for a single-page dashboard.
- **Scheduled Ingestion vs Live Search**: I chose a scheduled ingestion model (every 12-24 hours) for the PoC. This prevents the user from waiting 20+ seconds for a live scrape to finish and avoids triggering Google's rate limits too quickly.
- **Fixed Origin (SFO)**: Fixed to SFO to demonstrate the "anywhere" discovery feature within a constrained scraping scope.

## 🚧 What Breaks Under Pressure
- **Google Selector Changes**: While I use stream interception for data, the initial navigation (entering origin/destination) still relies on selectors. If Google changes these, the scraper's "search" phase will fail.
- **IP Blocking**: Running this on a single server IP without a residential proxy rotator will eventually lead to 429 errors from Google.

## 🚀 Future Roadmap
1. **Distributed Scraping**: Transition to Celery/RabbitMQ to support multiple origin cities and longer date ranges.
2. **Multi-Stop Discovery**: Enhance the Protobuf parser to extract complex multi-leg journeys and layover details.
3. **Price Alerts**: Add a user system to subscribe to AI-monitored price drops on specific routes.
