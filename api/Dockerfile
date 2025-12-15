FROM python:3.11-slim

WORKDIR /app
COPY . .

# Install uv (since you're using pyproject.toml + uv.lock)
RUN pip install --no-cache-dir uv \
    && uv sync --frozen

# Cloud Run listens on 8080
EXPOSE 8080

# Start FastAPI (your file is main.py)
CMD ["bash", "-lc", "uv run uvicorn main:app --host 0.0.0.0 --port 8080"]
