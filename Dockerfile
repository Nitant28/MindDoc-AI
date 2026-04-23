# --- Stage 1: Build Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npx vite build

# --- Stage 2: Backend Runtime ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y \
    gcc \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ app/
COPY scripts/ scripts/
COPY main.py .
COPY run_server.py .
COPY config.py .

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /build/frontend/dist frontend/dist

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/health')" || exit 1

# Run server
CMD ["python", "run_server.py"]
