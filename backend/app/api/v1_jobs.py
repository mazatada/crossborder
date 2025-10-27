from flask import Blueprint, jsonify, abort, current_app, g
from sqlalchemy import create_engine, text

bp = Blueprint("jobs_v1", __name__)

def _get_engine():
    if not hasattr(g, "engine"):
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI") or current_app.config.get("DATABASE_URL")
        if not uri:
            abort(500, description="DB URI not configured")
        g.engine = create_engine(uri, pool_pre_ping=True, future=True)
    return g.engine

@bp.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    engine = _get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT to_jsonb(j) AS job FROM public.jobs AS j WHERE j.id = :id"),
            {"id": job_id},
        ).mappings().first()
    if not row:
        abort(404)
    return jsonify(row["job"])
