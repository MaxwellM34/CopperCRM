import os
from dotenv import load_dotenv
from .base import BaseConfig

load_dotenv()

class LocalConfig(BaseConfig):
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASS = os.getenv("PG_PASS", "")
    PG_DB   = os.getenv("PG_DB", "postgres")

    GOOGLE_AUDIENCE = os.getenv("GOOGLE_AUDIENCE") #type: ignore
    SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
    DEBUG_AUTH = os.getenv("DEBUG_AUTH", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
    AUTO_PROVISION_USERS = os.getenv("AUTO_PROVISION_USERS", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }

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


'''
docker run -d \
  --name crm-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=crm_local \
  -p 5432:5432 \
  postgres:16
'''
