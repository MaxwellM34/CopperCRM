# utils/openai_schema.py
import copy
import json

from fastapi import FastAPI

from config import Config


def write_openai_schema(app: FastAPI, filename: str = "openai_tools.json") -> None:
    # First get the openapi schema.
    # NOTE: app.openapi() caches the schema; deep-copy so we don't mutate what FastAPI serves at /openapi.json.
    open_api_schema = copy.deepcopy(app.openapi())

    # Now write the "servers" section (which isn't there by default).
    # Use a full URL so clients don't treat the host as a path segment.
    server_url = getattr(Config, "SERVER_URL", None) or "http://localhost:8000"
    open_api_schema["servers"] = [{"url": server_url}]

    # Finally, write to file
    with open(filename, "w") as f:
        json.dump(open_api_schema, f, indent=2)
