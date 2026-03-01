from flask import Blueprint, jsonify, request
from ..models import AuditEvent
from ..db import db
from ..auth import require_api_key

bp = Blueprint("audit", __name__, url_prefix="/v1")


@bp.get("/audit/trace/<trace_id>")
@require_api_key
def audit_trace(trace_id):
    rows = (
        db.session.query(AuditEvent)
        .filter_by(trace_id=trace_id)
        .order_by(AuditEvent.ts.asc())
        .all()
    )
    return jsonify(
        events=[
            {
                "id": r.id,
                "trace_id": r.trace_id,
                "event": r.event,
                "payload": r.payload,
                "ts": (r.ts.isoformat() + "Z") if r.ts else None,
            }
            for r in rows
        ]
    )


@bp.get("/audit/recent")
@require_api_key
def audit_recent():
    limit = request.args.get("limit", 20, type=int)
    rows = (
        db.session.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit).all()
    )
    return jsonify(
        events=[
            {
                "id": r.id,
                "trace_id": r.trace_id,
                "event": r.event,
                "payload": r.payload,
                "ts": (r.ts.isoformat() + "Z") if r.ts else None,
            }
            for r in rows
        ]
    )
