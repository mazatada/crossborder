import hmac
import hashlib
import json
from typing import Dict, Any


def canonicalize_payload(payload: Dict[str, Any]) -> str:
    """
    Canonicalize payload for HMAC signature.
    Uses compact JSON separators and sorted keys.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def generate_signature(payload: Dict[str, Any], secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: Dictionary to sign
        secret: HMAC secret key

    Returns:
        Hex-encoded signature string
    """
    payload_str = canonicalize_payload(payload)
    signature = hmac.new(
        secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(payload: Dict[str, Any], signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature for webhook payload.

    Args:
        payload: Dictionary that was signed
        signature: Hex-encoded signature to verify
        secret: HMAC secret key

    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)
