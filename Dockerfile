FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AI_MONEY_TOWN_DB=/app/data/town.db \
    AI_MONEY_TOWN_WORKSPACE=/app/workspace \
    AI_MONEY_TOWN_ALLOW_REMOTE_OLLAMA=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

RUN mkdir -p /app/data /app/workspace \
    && python -m compileall -q /app/backend/app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.server:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
