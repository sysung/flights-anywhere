# Walkthrough: SFO Anywhere Flights

This guide walks you through the core features and the underlying technology of the SFO Anywhere Flights search engine.

## 1. The Dashboard
When you first open the application at `http://localhost:8000`, you are presented with a modern, split-pane dashboard:
- **Left Panel**: A structured data grid showing the latest flights scraped from Google Flights.
- **Right Panel**: A Gemini-powered AI assistant ready to help you discover routes.

## 2. Real-Time Scraper Status
In the top right of the header, you can see the **Scraper Status Badge**.
- It shows whether the background ingestion job is `RUNNING`, `SUCCESS`, or `FAILED`.
- Hovering over it reveals the number of records inserted and updated during the last run.
- The scraper runs automatically on startup and then every 12-24 hours.

## 3. Intelligent AI Search
Instead of manually tweaking filters, try talking to the assistant:
1. Type: *"Find me flights to London under $800"* in the chat box.
2. The agent will respond conversationally.
3. **The Magic**: Watch the **Quick Filters** and the **Flights Grid** update automatically. The agent extracted "LHR" (London Heathrow) and "$800" as structured criteria and synced them to the UI.

## 4. Quick Filters
If you prefer manual control, use the filters above the table:
- **Max Price Slider**: Instantly narrow down results by price.
- **Destination Autocomplete**: Search for specific 3-letter airport codes.
- **Airlines Multi-Select**: Filter by one or more specific carriers.
- **Sync**: Any changes you make here are also reflected in the AI assistant's "Active Filters" chip bar.

## 5. Booking Links
Every flight in the list includes a **"Book Flight"** button. Clicking this will open a pre-populated Google Flights search for that exact route and date, allowing you to complete your purchase directly with the airline.

## 6. Under the Hood
- **Binary Stream Parsing**: The backend doesn't just "scrape" HTML; it intercepts Google's internal binary Wiz stream and decodes the Protobuf payloads.
- **Modular Backend**: Built with FastAPI and PostgreSQL, organized into clean, scalable submodules.
- **Dockerized**: The entire environment (DB, App, Scraper) spins up with a single `docker-compose up --build` command.
