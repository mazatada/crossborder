from datetime import datetime
from typing import Tuple, Any, Dict, Optional, List

from flask import Blueprint, jsonify, request, Response
from app.auth import require_api_key
from app.db import db
from app.models import HSClassification
from app.audit import log_event

bp = Blueprint("v1_hs_review", __name__, url_prefix="/v1")


def _error_404() -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": "not_found",
                    "message": "not found",
                    "field": "id",
                    "severity": "block",
                }
            }
        ),
        404,
    )


def _error_409() -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": "conflict",
                    "message": "locked",
                    "field": "status",
                    "severity": "block",
                }
            }
        ),
        409,
    )


def _risk_flags_to_array(risk_flags: Any) -> List[Dict[str, Any]]:
    if isinstance(risk_flags, list):
        return risk_flags
    if isinstance(risk_flags, dict):
        result = []
        if risk_flags.get("ad_cvd"):
            result.append(
                {
                    "code": "ad_cvd",
                    "severity": "medium",
                    "description": "AD/CVD risk flag",
                }
            )
        if risk_flags.get("import_alert"):
            result.append(
                {
                    "code": "import_alert",
                    "severity": "high",
                    "description": "Import alert risk flag",
                }
            )
        return result
    return []


def _status_for_record(record: HSClassification) -> str:
    if record.reviewed_at or record.reviewed_by or record.review_comment:
        return "reviewed"
    if record.final_hs_code:
        return "classified"
    return "pending"


def _serialize(record: HSClassification) -> Dict[str, Any]:
    duty_rate = record.duty_rate if isinstance(record.duty_rate, dict) else None
    return {
        "id": str(record.id),
        "trace_id": record.trace_id,
        "product_id": record.product_id,
        "status": record.status or _status_for_record(record),
        "hs_candidates": record.hs_candidates or [],
        "final_hs_code": record.final_hs_code,
        "final_source": record.final_source or "system",
        "duty_rate": duty_rate,
        "duty_rate_override": record.duty_rate_override,
        "risk_flags": _risk_flags_to_array(record.risk_flags),
        "review_required": bool(record.review_required),
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "review_comment": record.review_comment,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@bp.get("/hs-classifications/<id>")
@require_api_key
def get_hs_classification(id: str) -> Tuple[Response, int]:
    record = db.session.get(HSClassification, id)
    if record is None:
        return _error_404()
    return jsonify(_serialize(record)), 200


@bp.put("/hs-classifications/<id>")
@require_api_key
def update_hs_classification(id: str) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.get(HSClassification, id)
    if record is None:
        return _error_404()
    if record.status == "locked":
        return _error_409()

    data = request.get_json(silent=True) or {}

    if "final_hs_code" in data:
        record.final_hs_code = data.get("final_hs_code") or record.final_hs_code
    if "final_source" in data:
        record.final_source = data.get("final_source") or record.final_source
    if "duty_rate_override" in data:
        override = data.get("duty_rate_override")
        if override and isinstance(override, dict):
            if "ad_valorem_pct" in override and "ad_valorem_rate" not in override:
                if override["ad_valorem_pct"] is not None:
                    override["ad_valorem_rate"] = round(override["ad_valorem_pct"] / 100.0, 5)
            elif "ad_valorem_rate" in override and "ad_valorem_pct" not in override:
                if override["ad_valorem_rate"] is not None:
                    override["ad_valorem_pct"] = round(override["ad_valorem_rate"] * 100.0, 3)
        record.duty_rate_override = override
    if "review_required" in data:
        record.review_required = bool(data.get("review_required"))
    if "review_comment" in data:
        record.review_comment = data.get("review_comment")
    if "reviewed_by" in data:
        record.reviewed_by = data.get("reviewed_by")

    if record.reviewed_by or record.review_comment:
        record.reviewed_at = record.reviewed_at or datetime.utcnow()
    record.status = _status_for_record(record)

    db.session.add(record)
    db.session.commit()

    log_event(
        trace_id=record.trace_id,
        event="hs.review.update",
        target_type="hs_classification",
        target_id=record.id,
        review_required=record.review_required,
    )

    return jsonify(_serialize(record)), 200
