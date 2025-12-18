FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir uv && uv sync --frozen

ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-lc", "cd /app && uv run uvicorn main:app --host 0.0.0.0 --port $PORT"]
