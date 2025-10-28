from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.db import db
from app.models import Job

bp = Blueprint("v1_pn", __name__, url_prefix="/v1")

@bp.post("/fda/prior-notice")
def fda_prior_notice():
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    product = data.get("product")
    logistics = data.get("logistics")
    importer = data.get("importer")
    consignee = data.get("consignee")

    if not trace_id or product is None or logistics is None or importer is None or consignee is None:
        return jsonify({"status":"error","error":{"code":"INVALID_ARGUMENT","message":"traceId, product, logistics, importer, consignee は必須"}}), 400

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=func.now(),
        payload_json=data,
        trace_id=trace_id
    )
    db.session.add(job); db.session.commit()
    return jsonify({"job_id": job.id, "status": "queued"}), 202
