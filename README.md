# SFO Anywhere Flights - Search & AI Assistant

An intelligent flight discovery dashboard and AI Assistant enabling users to find the lowest flights from SFO (San Francisco) with flexible search criteria and natural language chat synchronization.

🚀 **Live Deployed App URL**: [https://flights-anywhere-production.up.railway.app](https://flights-anywhere-production.up.railway.app)

---

## 🚀 Quick Start (Local Development)

Follow these steps to run the full stack locally. No cloud permissions are required.

### 1. Set Up Environment
Copy the template and add your `GOOGLE_CLOUD_API_KEY`:
```bash
cp .env.example .env
```

### 2. Launch with Docker
```bash
docker-compose up --build
```
The app will be available at **`http://localhost:8000`**.

### 3. Run Automated Tests
*   **Backend**: `docker-compose run --rm -e PYTHONPATH=/workspace app pytest app/tests/`
*   **Frontend**: `npm run test --prefix frontend`

---

## ⚙️ Configuration & Deployment

### Custom Database
To use an external PostgreSQL database instead of the default local container:
```bash
export DATABASE_URL="postgresql://user:pass@host:port/db"
docker-compose up
```

### Frontend Development (npm)
For active frontend development without rebuilding the Docker container:
*   `npm run dev`: Start the frontend development server.
*   `npm run build`: Build the production frontend assets.

### Production (Railway)
Updates are automatically deployed when changes are pushed to the `main` branch. Alternatively, if you have deployment permissions, you can use the Railway CLI:
```bash
railway up --service <service-name>
```
*Note: Production environments automatically use internal Railway networking for database connections.*
