import os
from .base import BaseConfig

class LocalConfig(BaseConfig):
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASS = os.getenv("PG_PASS", "")
    PG_DB   = os.getenv("PG_DB", "postgres")

    GOOGLE_AUDIENCE = os.getenv("GOOGLE_AUDIENCE") #type: ignore
    SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")

    TORTOISE_ORM = {
        "connections": {
            "default": f"postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
