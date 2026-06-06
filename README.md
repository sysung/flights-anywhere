# SFO Anywhere Flights - Search & AI Assistant

An intelligent flight discovery dashboard and AI Assistant enabling users to find the lowest flights from SFO (San Francisco) with flexible search criteria and natural language chat synchronization.

🚀 **Live Deployed App URL**: [https://flights-anywhere-production.up.railway.app](https://flights-anywhere-production.up.railway.app)

---

## 🚀 Quick Start Guide

### 1. Set Up Environment
Copy the example environment file and insert your **`GOOGLE_CLOUD_API_KEY`**:
```bash
cp .env.example .env
```

### 2. Run Locally (Docker Compose)
Start the PostgreSQL database and FastAPI web server:
```bash
docker-compose up --build
```
Access the local dashboard: **`http://localhost:8000`**

### 3. Build & Development (npm)
A root `package.json` is provided to delegate commands to the frontend:
- **`npm run build`**: Build the production frontend.
- **`npm run dev`**: Start the frontend development server.

### 4. Run Automated Tests
```bash
docker-compose run --rm -e PYTHONPATH=/workspace app pytest app/tests/
```

---

## 🧪 Multi-Environment Testing Strategy

- **Local Development**: Runs `docker-compose up`. The web application automatically connects to the isolated local PostgreSQL container.
- **Testing against External Database**: Point the local application to an external database by setting the `DATABASE_URL` environment variable before running `docker-compose up`:
  ```bash
  export DATABASE_URL="postgresql://<username>:<password>@<host>:<port>/<database>"
  docker-compose up
  ```
  Unset `DATABASE_URL` to return to using the local PostgreSQL container.
- **Production (Railway)**: Automatically binds to the provided database environment variable upon deploy.


---

## 🏗️ System Architecture

- **Frontend (React + MUI)**: Responsive split-pane dashboard. Displays the flight data grid, active filters chips, and the Gemini-powered AI chatbot assistant (now in a sleek blue theme).
- **Backend (FastAPI)**: Modularized structure for scalability:
    - `app/core/`: Configuration and AI agent logic.
    - `app/db/`: Database models, schemas, and session management.
    - `app/scraper/`: Playwright-based Google Flights scraper and stream parsing.
- **Scraper (Playwright)**: Scheduled crawler intercepting Google Flights stream results to ingest routes.
- **Database (PostgreSQL)**: Managed OLTP store for flights and scraper logs.

---

## 📝 Scalability Notes

- **Anti-Bot Protections**: Transition to residential proxy rotators or aggregator APIs in production.
- **Data Scaling**: Migrate background tasks to a distributed task queue (e.g. Celery + RabbitMQ) to support multiple origins.
- **DB Indexing**: Implement indexes on `(origin, destination, departure_date, price)` and partition tables by date ranges for high-concurrency queries.
