FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir uv && uv sync --frozen

# IMPORTANT: run from /app/api so "main:app" works
WORKDIR /app/api

ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-lc", "uv run uvicorn main:app --host 0.0.0.0 --port $PORT"]
