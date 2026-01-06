import base64
import hashlib
import hmac
from typing import Optional

from cryptography.fernet import Fernet

from config import Config


def _get_fernet() -> Fernet:
    key = Config.THREADS_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("THREADS_ENCRYPTION_KEY is not set")
    return Fernet(key.encode())


def encrypt_text(plaintext: str) -> bytes:
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes) -> str:
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext).decode("utf-8")


def _get_hmac_key() -> bytes:
    key = Config.THREADS_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("THREADS_ENCRYPTION_KEY is not set")
    raw = key.encode("utf-8")
    try:
        return base64.urlsafe_b64decode(raw)
    except Exception:
        return raw


def hmac_sha256(value: str, *, namespace: Optional[str] = None) -> str:
    key = _get_hmac_key()
    payload = value if namespace is None else f"{namespace}:{value}"
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
