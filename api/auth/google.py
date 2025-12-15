from fastapi.security import HTTPBearer
from google.oauth2 import id_token

from config import Config
from models import User

bearer = HTTPBearer(auto_error=False)

try:
    from google.auth.transport.requests import Request as _GoogleAuthRequest
except Exception:
    _GoogleAuthRequest = None


class _HttpClientRequest:
    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
        import http.client as http_client
        import socket
        import ssl
        import urllib.parse

        from google.auth import exceptions
        from google.auth.transport._http_client import Response

        if timeout is None:
            timeout = socket._GLOBAL_DEFAULT_TIMEOUT
        if headers is None:
            headers = {}

        parts = urllib.parse.urlsplit(url)
        path = urllib.parse.urlunsplit(("", "", parts.path, parts.query, parts.fragment))

        if parts.scheme == "http":
            connection = http_client.HTTPConnection(parts.netloc, timeout=timeout)
        elif parts.scheme == "https":
            context = ssl.create_default_context()
            connection = http_client.HTTPSConnection(
                parts.netloc, timeout=timeout, context=context
            )
        else:
            raise exceptions.TransportError(
                f"Unsupported URL scheme for token verification: {parts.scheme}"
            )

        try:
            connection.request(method, path, body=body, headers=headers, **kwargs)
            response = connection.getresponse()
            return Response(response)
        except (http_client.HTTPException, socket.error) as caught_exc:
            raise exceptions.TransportError(caught_exc) from caught_exc
        finally:
            connection.close()


def _get_google_request():
    if _GoogleAuthRequest is not None:
        return _GoogleAuthRequest()
    return _HttpClientRequest()


async def verify_google_token_db(token: str):
    try:
        req = _get_google_request()
        decoded = id_token.verify_oauth2_token(token, req, Config.GOOGLE_AUDIENCE)
        email = decoded.get("email")

        if not email:
            return None

        # Lookup or auto-provision user
        user = await User.get_or_none(email=email)
        if not user:
            if getattr(Config, "AUTO_PROVISION_USERS", False):
                firstname = (
                    decoded.get("given_name")
                    or decoded.get("name")
                    or str(email).split("@", 1)[0]
                    or "User"
                )
                lastname = decoded.get("family_name")

                user = await User.create(
                    email=email,
                    firstname=firstname,
                    lastname=lastname,
                )
            else:
                # reject unknown users
                return None

        return user

    except Exception as e:
        if getattr(Config, "DEBUG_AUTH", False):
            print(f"[auth] verify_google_token_db failed: {type(e).__name__}: {e}")
        return None

