# Single-container image: engine + API + built frontend (served by FastAPI). Used by Railway / any Docker host.
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# onnxruntime, which the OCR cross-check runs on, links against libgomp. The slim image does not carry it, and
# because the recogniser is imported lazily the miss surfaced as "the check could not be run" on every sheet
# rather than as a missing dependency at build time.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY engine /app/engine
COPY backend /app/backend
RUN pip install --no-cache-dir -e /app/engine
COPY --from=frontend /fe/dist /app/frontend/dist
# Left empty on purpose: an image that bakes in the word "unknown" answers the question "which code is running?"
# with something that looks like an answer, and the platform's own commit variable is then never consulted.
ARG VVS_BUILD=""
ENV VVS_BUILD=${VVS_BUILD}
ENV VVS_STATIC_DIR=/app/frontend/dist \
    VVS_STORAGE_ROOT=/data/storage \
    VVS_DATABASE_URL=sqlite:////data/vvs.db
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
