# backend/app/auth.py
import os, hmac
from flask import request
from .errors import error_response

def _parse_keys():
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]

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
            resp.headers["WWW-Authenticate"] = 'Bearer realm="api", error="invalid_token"'
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
