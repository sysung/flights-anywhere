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
- **Production (Railway)**: Automatically binds to the provided database environment variable upon deploy. **Tip**: Use the internal `DATABASE_URL` (private networking) instead of `DATABASE_PUBLIC_URL` in your Railway settings to avoid egress fees.

---

## ☁️ Deployment Guide (Railway)

Follow these steps to deploy this application to production using [Railway](https://railway.app):

### 1. Provision Services
1.  Log in to Railway and create a **New Project**.
2.  Select **Provision PostgreSQL**.
3.  Select **Deploy from GitHub repo** and connect this repository.

### 2. Configure Environment Variables
In your Railway **App** service settings, add the following variables:
- `GOOGLE_CLOUD_API_KEY`: Your Gemini API key.
- `DATABASE_URL`: Set this to `${{Postgres.DATABASE_URL}}` (This ensures you use the **private** internal network).
- `TIMEZONE`: `America/Los_Angeles` (or your preferred PST timezone).

### 3. Build & Launch
Railway normally uses **Nixpacks** by default. To ensure it uses the `Dockerfile` and deploys automatically:

1.  **Set Builder**: Go to **Settings > Build > Builder** in your App service and select **Dockerfile**.
2.  **Enable Automatic Deploys**: Ensure **Settings > General > Automatic Deployments** is turned ON.
3.  **Deploy via Push**: Once configured, every `git push` to your main branch will trigger a fresh build and deploy.
4.  **Deploy via CLI (Optional)**: If you need to deploy local changes without pushing to GitHub, you can still use the CLI:
    ```bash
    railway up
    ```

*Note: The background scraper will automatically trigger its first run upon successful deployment.*

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
