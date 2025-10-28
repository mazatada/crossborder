from flask import Blueprint, jsonify
from datetime import datetime
import os

bp = Blueprint("v1_misc", __name__, url_prefix="/v1")

@bp.get("/health")
def health():
    return jsonify(status="ok", ts=datetime.utcnow().isoformat() + "Z")

@bp.get("/version")
def version():
    return jsonify(
        version=os.getenv("APP_VERSION", "1.0.0"),
        commit=os.getenv("COMMIT", "dev"),
    )
