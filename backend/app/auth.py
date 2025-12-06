# backend/app/auth.py
import os
import hmac
from flask import request
from functools import wraps
from .errors import error_response


def _parse_keys():
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def require_api_key(f):
    """APIキー認証デコレータ"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        allowed = _parse_keys()

        # API_KEYS未設定なら認可スキップ
        if not allowed:
            return f(*args, **kwargs)

        auth = request.headers.get("Authorization", "")
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            resp = error_response(
                status=401,
                err_class="Unauthorized",
                message="missing bearer token",
                code="UNAUTHORIZED",
            )
            resp.headers["WWW-Authenticate"] = (
                'Bearer realm="api", error="invalid_token"'
            )
            return resp

        token = parts[1]
        for k in allowed:
            if hmac.compare_digest(token, k):
                return f(*args, **kwargs)

        resp = error_response(
            status=401,
            err_class="Unauthorized",
            message="invalid token",
            code="UNAUTHORIZED",
        )
        resp.headers["WWW-Authenticate"] = 'Bearer realm="api", error="invalid_token"'
        return resp

    return decorated_function


def install_api_key_protection(app, exempt_prefixes=None):
    if exempt_prefixes is None:
        exempt_prefixes = []

    allowed = _parse_keys()

    @app.before_request
    def _enforce():
        # API_KEYS 未設定なら認可スキップ
        if not allowed:
            return None

        # 例外パス（ヘルスチェック等）
        path = request.path or "/"
        for p in exempt_prefixes:
            if path.startswith(p):
                return None

        auth = request.headers.get("Authorization", "")
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            resp = error_response(
                status=401,
                err_class="Unauthorized",
                message="missing bearer token",
                code="UNAUTHORIZED",
            )
            resp.headers["WWW-Authenticate"] = (
                'Bearer realm="api", error="invalid_token"'
            )
            return resp

        token = parts[1]
        for k in allowed:
            if hmac.compare_digest(token, k):
                return None

        resp = error_response(
            status=401,
            err_class="Unauthorized",
            message="invalid token",
            code="UNAUTHORIZED",
        )
        resp.headers["WWW-Authenticate"] = 'Bearer realm="api", error="invalid_token"'
        return resp
