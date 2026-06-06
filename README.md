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

### 3. Run Automated Tests
```bash
docker-compose run --rm -e PYTHONPATH=/workspace app pytest app/tests/
```

---

## 🧪 Multi-Environment Testing Strategy

- **Local Development**: Runs `docker-compose up`. The web application automatically connects to the isolated local PostgreSQL container.
- **Local Testing against Production (Railway DB)**: Set the `DATABASE_URL` env variable to your Railway public database connection string:
  ```bash
  export DATABASE_URL="postgresql://postgres:REDACTED@acela.proxy.rlwy.net:46865/railway"
  docker-compose up
  ```
- **Switching Back to Local DB**: If you want to return to testing against the local container database, simply run `unset DATABASE_URL` in your terminal or remove `DATABASE_URL` from your local `.env` file, then run `docker-compose up`. The app service will fall back to using the local Postgres container.
- **Production (Railway)**: The container is deployed via `Dockerfile` and securely binds to the internal database port automatically. Pushing commits to `main` branch redeploys the service.

---

## 🏗️ System Architecture

- **Frontend (React + MUI)**: Responsive split-pane dashboard. Displays the flight data grid, active filters chips, and the Gemini-powered AI chatbot assistant.
- **Backend (FastAPI)**: REST endpoints (`/api/flights`, `/api/scraper/status`, `/api/chat`) and serves compiled React assets.
- **Scraper (Playwright)**: Scheduled crawler intercepting Google Flights stream results to ingest routes.
- **Database (PostgreSQL)**: Managed OLTP store for flights and scraper logs.

---

## 📝 Scalability Notes

- **Anti-Bot Protections**: Transition to residential proxy rotators or aggregator APIs in production.
- **Data Scaling**: Migrate background tasks to a distributed task queue (e.g. Celery + RabbitMQ) to support multiple origins.
- **DB Indexing**: Implement indexes on `(origin, destination, departure_date, price)` and partition tables by date ranges for high-concurrency queries.
