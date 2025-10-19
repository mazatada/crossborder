from flask import Blueprint, jsonify
from ..models import AuditEvent

bp = Blueprint("audit", __name__)

@bp.get("/audit/trace/<trace_id>")
def audit_trace(trace_id):
    rows = (AuditEvent.query
            .filter_by(trace_id=trace_id)
            .order_by(AuditEvent.ts.asc())
            .all())
    return jsonify(events=[
        {
            "id": r.id,
            "trace_id": r.trace_id,
            "event": r.event,
            "payload": r.payload,
            "ts": (r.ts.isoformat() + "Z") if r.ts else None,
        } for r in rows
    ])
