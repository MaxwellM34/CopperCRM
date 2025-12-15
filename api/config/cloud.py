import os
from .base import BaseConfig

class CloudConfig(BaseConfig):
    PG_GCP_PATH = os.getenv("PG_GCP_PATH")  # crm-mvp-481223:us-central1:crm-sql
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_USER = os.getenv("PG_USER")
    PG_PASS = os.getenv("PG_PASS")
    PG_DB   = os.getenv("PG_DB", "crm")

    GOOGLE_AUDIENCE = os.getenv("GOOGLE_AUDIENCE")
    SERVER_URL = os.getenv("SERVER_URL")

    _missing = [
        name
        for name, value in {
            "PG_GCP_PATH": PG_GCP_PATH,
            "PG_USER": PG_USER,
            "PG_PASS": PG_PASS,
        }.items()
        if not value
    ]
    if _missing:
        raise RuntimeError(
            "ENV=cloud requires the following environment variables: "
            + ", ".join(_missing)
            + " (or set ENV=local)."
        )

    TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": f"/cloudsql/{PG_GCP_PATH}",
                    "port": PG_PORT,
                    "user": PG_USER,
                    "password": PG_PASS,
                    "database": PG_DB,
                },
            }
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
