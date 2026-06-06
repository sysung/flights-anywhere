# Stage 1: Build the React + MUI Frontend
FROM node:18-slim AS node_builder
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Web Server and Scraper Environment
FROM mcr.microsoft.com/playwright/python:v1.41.2-jammy

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built assets from Stage 1 to workspace/dist
COPY --from=node_builder /frontend/dist /workspace/dist

# Copy the rest of the workspace files
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
