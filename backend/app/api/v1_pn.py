from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.db import db
from app.models import Job
from app.audit import record_event
import traceback
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("v1_pn", __name__, url_prefix="/v1")


@bp.post("/fda/prior-notice")
def fda_prior_notice():
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    product = data.get("product")
    logistics = data.get("logistics")
    importer = data.get("importer")
    consignee = data.get("consignee")

    if (
        not trace_id
        or product is None
        or logistics is None
        or importer is None
        or consignee is None
    ):
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "traceId, product, logistics, importer, consignee は必須",
                    },
                }
            ),
            400,
        )

    from app.logging_conf import get_trace_id
    try:
        job = Job(
            type="pn_submit",
            status="queued",
            attempts=0,
            next_run_at=func.now(),
            payload_json=data,
            trace_id=trace_id or get_trace_id(),
        )
        db.session.add(job)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        tb = traceback.format_exc()
        logger.error(f"fda/prior-notice DB error: {e}\n{tb}")
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

    # 監査（失敗しても202を返す）
    try:
        record_event(
            event="JOB_QUEUED",
            trace_id=trace_id,
            target_type="job",
            target_id=job.id,
            type=job.type,
        )
    except Exception:
        logger.warning("record_event failed in fda_prior_notice", exc_info=True)

    return jsonify({"job_id": job.id, "status": "queued"}), 202
