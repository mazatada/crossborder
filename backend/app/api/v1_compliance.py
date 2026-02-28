from typing import Tuple, Any, Dict, List

from flask import Blueprint, jsonify, Response
from app.auth import require_api_key
from app.db import db
from app.models import HSClassification, Job

bp = Blueprint("v1_compliance", __name__, url_prefix="/v1")


def _risk_flags_to_array(risk_flags: Any) -> List[Dict[str, Any]]:
    if isinstance(risk_flags, list):
        return risk_flags
    if isinstance(risk_flags, dict):
        result = []
        if risk_flags.get("ad_cvd"):
            result.append(
                {"code": "ad_cvd", "severity": "medium", "description": "AD/CVD risk"}
            )
        if risk_flags.get("import_alert"):
            result.append(
                {
                    "code": "import_alert",
                    "severity": "high",
                    "description": "Import alert risk",
                }
            )
        return result
    return []


@bp.get("/products/<product_id>/compliance")
@require_api_key
def get_compliance(product_id: str) -> Tuple[Response, int]:
    record = (
        db.session.query(HSClassification)
        .filter(HSClassification.product_id == product_id)
        .order_by(HSClassification.created_at.desc())
        .first()
    )
    if record is None:
        return (
            jsonify(
                {
                    "error": {
                        "class": "not_found",
                        "message": "not found",
                        "field": "product_id",
                        "severity": "block",
                    }
                }
            ),
            404,
        )

    docs_job = (
        db.session.query(Job)
        .filter(Job.trace_id == record.trace_id, Job.type == "clearance_pack")
        .order_by(Job.created_at.desc())
        .first()
    )
    pn_job = (
        db.session.query(Job)
        .filter(Job.trace_id == record.trace_id, Job.type == "pn_submit")
        .order_by(Job.created_at.desc())
        .first()
    )

    response = {
        "product_id": product_id,
        "trace_id": record.trace_id,
        "hs_classification": {
            "final_hs_code": record.final_hs_code,
            "final_source": record.final_source or "system",
            "review_required": bool(record.review_required),
            "status": record.status or "classified",
            "reviewed_by": record.reviewed_by,
            "reviewed_at": (
                record.reviewed_at.isoformat() if record.reviewed_at else None
            ),
            "risk_flags": _risk_flags_to_array(record.risk_flags),
        },
        "duty": None,
        "docs": (
            {
                "clearance_pack_job_id": str(docs_job.id) if docs_job else None,
                "clearance_pack_status": docs_job.status if docs_job else None,
                "prior_notice_required": bool(pn_job),
                "prior_notice_status": pn_job.status if pn_job else None,
            }
            if (docs_job or pn_job)
            else None
        ),
        "audit": {
            "last_updated_by": record.reviewed_by,
            "last_updated_at": (
                record.updated_at.isoformat()
                if record.updated_at
                else record.created_at.isoformat()
            ),
        },
    }
    return jsonify(response), 200
