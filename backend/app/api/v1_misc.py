from flask import Blueprint, jsonify
from datetime import datetime
import os

bp = Blueprint("misc", __name__)

@bp.get("/health")
def health():
    return jsonify(status="ok", ts=datetime.utcnow().isoformat() + "Z")

@bp.get("/version")
def version():
    return jsonify(
        version=os.getenv("APP_VERSION", "1.0.0"),
        commit=os.getenv("COMMIT", "dev"),
    )
