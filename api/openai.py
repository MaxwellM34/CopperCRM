# utils/openai_schema.py
import json
from fastapi import FastAPI



def write_openai_schema(app: FastAPI, filename='openai_tools.json'):
    # First get the openapi schema
    openApiSchema = app.openapi()
    # Now write the "servers" section (which isn't there by default).
    # Use a full URL so clients don't treat the host as a path segment.
    openApiSchema['servers'] = [{'url': 'http://localhost:8000'}]
    # Finally, write to file
    with open(filename, 'w') as f:
        json.dump(openApiSchema, f, indent=2)