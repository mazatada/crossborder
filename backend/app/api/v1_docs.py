from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.db import db
from app.models import Job
from app.audit import record_event
import traceback
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("v1_docs", __name__, url_prefix="/v1")


@bp.post("/docs/clearance-pack")
def docs_clearance_pack():
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    hs_code = data.get("hs_code")
    required = data.get("required_uom")
    invoice = data.get("invoice_uom")

    if not all([hs_code, required, invoice]):
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "hs_code/required_uom/invoice_uom は必須",
                    },
                }
            ),
            400,
        )

    from app.logging_conf import get_trace_id

    try:
        job = Job(
            type="clearance_pack",
            status="queued",
            attempts=0,
            next_run_at=func.now(),
            payload_json={
                "traceId": trace_id,
                "hs_code": hs_code,
                "required_uom": required,
                "invoice_uom": invoice,
                "invoice_payload": data.get("invoice_payload"),
            },
            trace_id=trace_id or get_trace_id(),
        )
        db.session.add(job)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        tb = traceback.format_exc()
        logger.error(f"docs/clearance-pack DB error: {e}\n{tb}")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "DB_ERROR",
                        "message": str(e),
                        "detail": tb,
                    },
                }
            ),
            500,
        )

    # コミット後に独立TXで監査（失敗しても202を返す）
    try:
        record_event(
            event="JOB_QUEUED",
            trace_id=trace_id,
            target_type="job",
            target_id=job.id,
            type=job.type,
        )
    except Exception:
        logger.warning("record_event failed in docs_clearance_pack", exc_info=True)

    return jsonify({"job_id": job.id, "status": "queued"}), 202
