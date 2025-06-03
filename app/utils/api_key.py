import hashlib
import secrets


def generate_api_key() -> tuple[str, str, str]:
    key_bytes = secrets.token_bytes(32)
    key_hex = key_bytes.hex()
    prefix = f"tk_{key_hex[:6]}"
    full_key = f"tk_{key_hex}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(api_key: str, stored_hash: str) -> bool:
    computed_hash = hash_api_key(api_key)
    return secrets.compare_digest(computed_hash, stored_hash)

def generate_drop_key(length: int = 8) -> str:
    return secrets.token_urlsafe(length)[:length]