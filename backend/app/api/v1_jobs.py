from flask import Blueprint, jsonify, request
from ..models import Job, Artifact
bp = Blueprint("jobs", __name__)

@bp.get("/jobs/<job_id>")
def get_job(job_id):
    j = Job.query.get_or_404(job_id)
    arts = Artifact.query.filter_by(job_id=job_id).all()
    return jsonify({
        "status": j.status,
        "type": j.type,
        "trace_id": j.trace_id,
        "artifacts": [{"type":a.type,"media_id":a.media_id,"sha256":a.sha256,"size":a.size} for a in arts],
        "error": j.error
    })
