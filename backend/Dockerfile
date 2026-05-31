# Stage base: Python + uv (instalador 10-100x más rápido que pip, escrito en Rust)
FROM python:3.13.13-slim-trixie AS base
WORKDIR /app
RUN pip install --no-cache-dir uv

# Stage dev: uvicorn con --reload, código montado por volumen
FROM base AS dev
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
COPY alembic.ini ./
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"]

# Stage prod: multi-worker, non-root, imagen autocontenida
FROM base AS prod
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
COPY src/ ./src/
COPY alembic.ini entrypoint.sh ./
ENV PYTHONPATH=/app/src
RUN addgroup --system --gid 1001 appgroup && \
    adduser  --system --uid 1001 --ingroup appgroup --no-create-home appuser
USER appuser
EXPOSE 8000
CMD ["./entrypoint.sh"]
