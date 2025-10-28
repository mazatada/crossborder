# backend/app/api/v1_jobs.py
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app.db import db
from app.models import Job

bp = Blueprint("v1_jobs", __name__, url_prefix="/v1")

@bp.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    job = db.session.get(Job, job_id)  # SQLAlchemy 2.x の get
    if not job:
        return jsonify({
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "リソースが見つかりません"}
        }), 404
    return jsonify({
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "attempts": job.attempts,
        "next_run_at": job.next_run_at,
        "payload_json": job.payload_json,
        "result_json": job.result_json,
        "error": job.error,
        "trace_id": job.trace_id,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    })

@bp.post("/jobs")
def create_job():
    data = request.get_json(silent=True) or {}
    jtype = data.get("type")
    payload = data.get("payload") or {}
    trace_id = data.get("trace_id")

    if not isinstance(jtype, str):
        return jsonify({"status":"error","error":{"code":"INVALID_ARGUMENT","message":"type は必須の文字列です"}}), 400
    if not isinstance(payload, dict):
        return jsonify({"status":"error","error":{"code":"INVALID_ARGUMENT","message":"payload はオブジェクトである必要があります"}}), 400

    job = Job(
        type=jtype, status="queued", attempts=0,
        next_run_at=func.now(), payload_json=payload, trace_id=trace_id
    )
    db.session.add(job)
    db.session.commit()
    return jsonify({"id": job.id, "status": "queued"}), 201
