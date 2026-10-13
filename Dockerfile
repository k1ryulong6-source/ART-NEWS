# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
# Optional CA mount for managed-proxy builds; normal local builds use system CA.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir -r requirements.txt; fi
COPY backend ./backend
COPY frontend ./frontend
COPY scripts ./scripts
COPY config ./config
COPY data ./data
COPY schema.sql ./
RUN python scripts/build_static.py
RUN useradd --create-home appuser && mkdir -p /app/runtime && chmod -R a+rX /app && chown appuser:appuser /app/runtime
USER appuser
ENV CULTURE_DESK_DB=/app/runtime/culture-desk.db
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
