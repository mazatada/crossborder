docker compose exec backend sh -lc 'python - << "PY"
from pathlib import Path
code = r"""
from flask import request, jsonify
import os, hmac

def _parse_keys():
    raw = os.getenv("API_KEYS", "")
    return [k.strip() for k in raw.split(",") if k.strip()]

def install_api_key_protection(app, exempt_prefixes=None):
    if exempt_prefixes is None:
        exempt_prefixes = []
    allowed = _parse_keys()

    @app.before_request
    def _check():
        path = request.path or ""

        # 免除パス（health/version/static）
        for p in exempt_prefixes:
            if path.startswith(p):
                return None

        # キー未設定ならスキップ（開発用）
        if not allowed:
            return None

        auth = request.headers.get("Authorization", "")
        parts = auth.split()

        # Bearer 無し → 401
        if len(parts) != 2 or parts[0].lower() != "bearer":
            resp = jsonify(error={
                "class": "Unauthorized",
                "message": "missing bearer token",
                "code": "UNAUTHORIZED",
            })
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = "Bearer realm=\\"api\\", error=\\"invalid_token\\""
            return resp

        token = parts[1]
        for k in allowed:
            if hmac.compare_digest(token, k):
                return None

        # 不正トークン → 401
        resp = jsonify(error={
            "class": "Unauthorized",
            "message": "invalid token",
            "code": "UNAUTHORIZED",
        })
        resp.status_code = 401
        resp.headers["WWW-Authenticate"] = "Bearer realm=\\"api\\", error=\\"invalid_token\\""
        return resp
"""
Path("/app/app/auth.py").write_text(code)
print("auth.py written OK")
PY'
