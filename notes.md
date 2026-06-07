# Notes: SFO Flight Anywhere Search (PoC)

## Prompt
Build a mini-app where AI does real work in the core feature and can be easily run/deployed.

## Goal
Create a flights search engine focusing on the "anywhere" discovery feature (initially from SFO), allowing users to find the lowest prices with flexible criteria and date options.

## User Requirements
- **Origin:** Fixed to San Francisco International Airport (SFO) for the PoC.
- **Date Range:** Flexible travel dates (initially restricted to the next 30 days to limit scraping load).
- **Advanced Filters:**
  - Maximum price.
  - Airline preferences.
  - Country inclusion/exclusion.
  - Duration/length of stay (e.g., number of days/weeks).
- **Interface:** A clean, responsive Web UI to search, filter, and discover flight options.
- **AI Chatbot:** An AI-Agentic chatbot will be implemented to do agentic workflows on top of the filters.

## Deliverables
- A simple, responsive web UI.
- A robust, easily runnable `docker-compose` setup.
- A PostgreSQL database seeded and updated with flight data.
- A Playwright scraper pipeline to collect SFO flight options from Google Flights.
- Documentation: `APPROACH.md`, `walkthrough.md`, and a demo video.

## Architecture & PoC Constraints
- **Data Source:** Playwright scraper harvesting Google Flights data for all outgoing SFO flights within the next month.
    - *Why standard flight APIs aren't viable:* Commercial options (Amadeus, Sabre) charge steep transactional GDS fees, return stale cached prices in sandbox environments, and have rigid schemas that prevent flexible "anywhere" queries.
    - *Why Google Flights is difficult:* Google actively obfuscates payloads using internal binary Protobuf RPCs, implements dynamic Wiz DOM selector changes, and enforces aggressive anti-bot rate limiting.
    - *PoC Approach & Date Constraint:* We will use a Playwright browser automation scraper targeting the Google Flights Explore page. Since Google Flights Explore requires a date parameters window, the PoC will restrict searches to a predefined explicit date range (e.g., 1-week trips within the next 30 days). Once this PoC is stable, we can scale it to support dynamic, open-ended date parameters.
- **Storage:** OLTP PostgreSQL database.
- **Orchestration:** Scheduled scraping runs (daily) that ingest data and perform soft-delete operations (marking outdated/removed flights with `delete_indicator = 1`).
- **Deployment:** The entire stack runs via a single `docker-compose up` command.

## Scalability Issues & Future Solutions (Post-PoC)
1. **Scraper Rate Limiting & Captchas:**
   - *PoC Limit:* Google Flights will rate-limit or block a single server IP if scraped aggressively.
   - *Scalability Solution:* Use residential proxy rotators, stealth plugins, and user-agent rotation. In production, transition to a paid aggregator API (like SerpApi or Skyscanner) or establish airline data feeds.
2. **Data Volume & Scraping Scope:**
   - *PoC Limit:* Limited to SFO flights for the next 30 days.
   - *Scalability Solution:* To expand to multiple origins and longer horizons (e.g., 3-6 months), replace the brute-force scraper with a message queue (like RabbitMQ/Celery) running distributed scraping workers.
3. **Database Performance:**
   - *PoC Limit:* Basic PostgreSQL database.
   - *Scalability Solution:* As routes and historical prices grow, implement database indexing on `(origin, destination, departure_date, price)`, partitioning by date ranges, and caching popular queries using Redis.
4. **Orchestration Complexity:**
   - *PoC Limit:* Simple scheduling within a task runner.
   - *Scalability Solution:* Transition to a full production orchestrator like Apache Airflow or Prefect to manage complex dependencies, retries, and data transformations via dbt.

```mermaid
graph TD
    User([User / Browser]) -->|HTTP / JSON| API[FastAPI Web Server /app]
    API -->|Read/Write| DB[(PostgreSQL /db)]
    
    subgraph Container: app
        API
        Scheduler[Background Scheduler] -->|Triggers| Scraper[Playwright Scraper]
        Scraper -->|Ingests Stage| DB
        Agent[AI Chatbot Agent] -->|Queries / Filters| DB
        API -->|Delegates Chat| Agent
    end
    
    subgraph Container: db
        DB
    end
    
    Scraper -->|Scrapes| GF((Google Flights))
    ```

    ## 🏗️ Future Database Schema Management (Source of Truth)
    To ensure the local development environment and Railway production instance stay in sync as the schema evolves:

    1. **Alembic (Industry Standard)**:
    - **Strategy**: Use Alembic to generate version-controlled migration scripts directly from SQLAlchemy models.
    - **Benefit**: Keeps database structure in Git, allows rollbacks, and ensures every environment (local/prod) is identical.
    - **Command**: `alembic revision --autogenerate -m "description"`

    2. **Atlas (IaaS approach)**:
    - **Strategy**: Leverage [Atlas](https://atlasgo.io/) for declarative schema management (Terraform for DBs).
    - **Benefit**: Automatic diffing between environments and visual schema visualizations.