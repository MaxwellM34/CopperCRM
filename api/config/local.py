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

    DB_URL = f"postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

    TORTOISE_ORM = {
        "connections": {"default": DB_URL},
        "apps": {
            "models": {
                "models": ["api.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }


TORTOISE_ORM = LocalConfig.TORTOISE_ORM

'''
docker run -d \
  --name crm-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=crm_local \
  -p 5432:5432 \
  postgres:16
'''
