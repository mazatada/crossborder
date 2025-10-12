from flask import Blueprint, jsonify, request
from ..models import Audit
bp = Blueprint("audit", __name__)

@bp.get("/audit/trace/<trace_id>")
def audit_trace(trace_id):
    events = Audit.query.filter_by(trace_id=trace_id).order_by(Audit.created_at.asc()).all()
    return jsonify([{"event":a.event,"payload":a.payload,"ts":a.created_at.isoformat()} for a in events])
