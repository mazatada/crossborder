from flask import Blueprint, request, jsonify
from app.db import db
from app.models import OrderStatus
from app.audit import record_event
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
import os

bp = Blueprint("v1_inbound", __name__, url_prefix="/v1/integrations")


@bp.post("/orders/<order_id>/status")
def receive_order_status(order_id: str):
    """Receive order status update from external system"""

    # Verify API key (get dynamically to support testing)
    api_key = request.headers.get("X-API-Key")
    expected_key = os.getenv("INBOUND_API_KEY", "dev-api-key-change-me")
    if api_key != expected_key:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "UNAUTHORIZED", "message": "Invalid API key"},
                }
            ),
            401,
        )

    data = request.get_json(silent=True) or {}

    status = data.get("status")
    ts_str = data.get("ts")
    customer_region = data.get("customer_region")

    # Validate required fields
    if not status or status not in ["PAID", "CANCELED"]:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "status must be PAID or CANCELED",
                    },
                }
            ),
            400,
        )

    if not ts_str:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "INVALID_ARGUMENT", "message": "ts is required"},
                }
            ),
            400,
        )

    # Parse timestamp
    try:
        ts_aware = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # タイムゾーン情報がない場合はUTCとして扱う（サーバーローカルTZ依存を防止）
        if ts_aware.tzinfo is None:
            ts_aware = ts_aware.replace(tzinfo=timezone.utc)
        ts = ts_aware.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "ts must be ISO 8601 format",
                    },
                }
            ),
            400,
        )

    # Check for existing record to ensure idempotency
    existing = db.session.query(OrderStatus).filter_by(
        order_id=order_id, status=status
    ).first()
    
    if existing:
        # Idempotent return explicitly without doing anything
        return jsonify({"status": "accepted", "order_id": order_id}), 202

    # Create order status record
    order_status = OrderStatus(
        order_id=order_id, status=status, ts=ts, customer_region=customer_region
    )

    db.session.add(order_status)
    try:
        db.session.commit()
    except IntegrityError:
        # Caught a race condition where another transaction inserted the same order_id+status
        db.session.rollback()
        return jsonify({"status": "accepted", "order_id": order_id}), 202

    # Record audit event
    record_event(
        event="ORDER_STATUS_RECEIVED",
        trace_id=f"order-{order_id}",
        order_id=order_id,
        status=status,
        customer_region=customer_region,
    )

    return jsonify({"status": "accepted", "order_id": order_id}), 202
