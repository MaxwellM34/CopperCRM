from fastapi.security import HTTPBearer
from google.oauth2 import id_token
from config import Config
from models import User

bearer = HTTPBearer(auto_error=False)


async def verify_google_token_db(token: str):
    try:
        from google.auth.transport import requests

        req = requests.Request()
        decoded = id_token.verify_oauth2_token(token, req, Config.GOOGLE_AUDIENCE)
        email = decoded.get('email')

        # Lookup or auto-provision user
        user = await User.get_or_none(email=email)
        if not user:
            # Option 1: return None (reject unknown users)
            return None

        return user

    except Exception:
        return None
