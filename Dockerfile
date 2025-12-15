FROM python:3.11-slim

WORKDIR /app
COPY . .

# install uv + deps
RUN pip install --no-cache-dir uv \
    && cd api \
    && uv sync --frozen

WORKDIR /app/api
ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-lc", "uv run uvicorn main:app --host 0.0.0.0 --port $PORT"]
