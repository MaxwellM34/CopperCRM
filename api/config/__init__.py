import os
from dotenv import load_dotenv
load_dotenv()

def _get_env() -> str:
    return os.getenv("ENV", "local").strip().lower()


_env = _get_env()

if _env == "cloud":
    from .cloud import CloudConfig as Config
else:
    from .local import LocalConfig as Config

__all__ = ["Config"]
