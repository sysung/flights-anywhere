# Stage 1: Build the React + MUI Frontend
FROM node:20-slim AS node_builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
# Increase memory limit for node to prevent OOM during build
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Stage 2: Python Web Server and Scraper Environment
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

# Configure default environment
ENV TZ=America/Los_Angeles
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
# Install blackboxprotobuf manually without its pinned dependencies to avoid protobuf conflict.
# We also install 'six' as it is a minimal pure-python requirement for blackboxprotobuf.
RUN pip install --no-cache-dir six
RUN pip install --no-cache-dir blackboxprotobuf==1.0.1 --no-deps
# Install the remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary application code and built assets
# This significantly shrinks the final image by excluding frontend source, docs, and git
COPY --from=node_builder /frontend/dist /workspace/dist
COPY app /workspace/app

EXPOSE 8000
# Use the PORT environment variable provided by Railway, defaulting to 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
