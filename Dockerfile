# ---- 1. build the React frontend --------------------------------------------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. Python API (serves the built frontend from the same origin) ---------
FROM python:3.11-slim
# INSTALL_ML=true adds torch (CPU) + sentence-transformers + EasyOCR and pre-downloads the models (~2 GB RAM at runtime).
# Leave it false for small hosts (e.g. Render free, 512 MB): the app falls back to offline hashing embeddings.
ARG INSTALL_ML=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TRANSFORMERS_NO_TF=1 HF_HOME=/models
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_ML" = "true" ]; then \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir -r requirements-ml.txt && \
      python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"; \
    fi
COPY app/ app/
COPY run_server.py .
COPY --from=web /web/dist frontend/dist
RUN useradd -m minddoc && mkdir -p /data /models && chown -R minddoc /app /data /models
USER minddoc
# Everything stateful lives under /data so one persistent volume/disk keeps the DB and the uploaded originals.
ENV DATABASE_URL=sqlite:////data/minddoc.db STORAGE_DIR=/data/uploads HOST=0.0.0.0 PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/api/health')"
CMD ["python", "run_server.py"]
