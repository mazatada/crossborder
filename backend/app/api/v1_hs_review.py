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
    # 既存の明確なステータスを優先する場合はここでガードする
    if record.status in ["locked"]:
        return record.status

    if record.reviewed_at and record.final_hs_code:
        return "reviewed"
    if record.final_hs_code:
        return "classified"
    if record.reviewed_by:
        return "in_progress"
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


@bp.get("/hs-classifications/<int:id>")
@require_api_key
def get_hs_classification(id: int) -> Tuple[Response, int]:
    record = db.session.get(HSClassification, id)
    if record is None:
        return _error_404()
    return jsonify(_serialize(record)), 200


@bp.put("/hs-classifications/<int:id>")
@require_api_key
def update_hs_classification(id: int) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.query(HSClassification).filter_by(id=id).with_for_update().first()
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
            pct_val = override.get("ad_valorem_pct")
            rate_val = override.get("ad_valorem_rate")
            # 非数値の入力をガードして 400 を返す
            if pct_val is not None and not isinstance(pct_val, (int, float)):
                return jsonify({"error": "ad_valorem_pct must be a number"}), 400
            if rate_val is not None and not isinstance(rate_val, (int, float)):
                return jsonify({"error": "ad_valorem_rate must be a number"}), 400
            if "ad_valorem_pct" in override and "ad_valorem_rate" not in override:
                if pct_val is not None:
                    override["ad_valorem_rate"] = round(pct_val / 100.0, 5)
            elif "ad_valorem_rate" in override and "ad_valorem_pct" not in override:
                if rate_val is not None:
                    override["ad_valorem_pct"] = round(rate_val * 100.0, 3)
        record.duty_rate_override = override
    if "review_required" in data:
        req_val = data.get("review_required")
        if not isinstance(req_val, bool):
            return jsonify({"error": "Invalid field: review_required must be a boolean"}), 400
        record.review_required = req_val
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


@bp.get("/reviews/hs")
@require_api_key
def list_hs_reviews() -> Tuple[Response, int]:
    status = request.args.get("status")
    q = db.session.query(HSClassification)
    if status:
        q = q.filter(HSClassification.status == status)  # type: ignore
    
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    
    total = q.count()
    records = q.order_by(HSClassification.id.desc()).offset((page - 1) * limit).limit(limit).all()  # type: ignore

    return jsonify({
        "data": [_serialize(r) for r in records],
        "meta": {"total": total, "page": page, "limit": limit}
    }), 200


@bp.post("/reviews/hs/<int:id>/assign")
@require_api_key
def assign_hs_review(id: int) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.query(HSClassification).filter_by(id=id).with_for_update().first()
    if record is None:
        return _error_404()
    if record.status == "locked":
        return _error_409()
        
    data = request.get_json(silent=True) or {}
    operator_id = data.get("operator_id")
    if not operator_id:
        return jsonify({"error": "Missing required field: operator_id"}), 400
        
    record.reviewed_by = operator_id
    record.status = _status_for_record(record)
    
    db.session.add(record)
    db.session.commit()
    
    trace_id = request.headers.get("X-Trace-Id") or record.trace_id
    log_event(
        trace_id=trace_id, 
        event="hs.review.assigned", 
        target_type="hs_classification", 
        target_id=record.id, 
        operator_id=operator_id
    )
    return jsonify(_serialize(record)), 200


@bp.post("/reviews/hs/<int:id>/lock")
@require_api_key
def lock_hs_review(id: int) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.query(HSClassification).filter_by(id=id).with_for_update().first()
    if record is None:
        return _error_404()
        
    if record.status == "locked":
        return _error_409()
        
    record.status = "locked"
    
    operator_id = request.headers.get("X-Operator-Id")
    if operator_id:
        record.locked_by = operator_id
        
    db.session.add(record)
    db.session.commit()
    
    trace_id = request.headers.get("X-Trace-Id") or record.trace_id
    log_event(
        trace_id=trace_id, 
        event="hs.review.locked", 
        target_type="hs_classification", 
        target_id=record.id
    )
    return jsonify(_serialize(record)), 200


@bp.post("/reviews/hs/<int:id>/finalize")
@require_api_key
def finalize_hs_review(id: int) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.query(HSClassification).filter_by(id=id).with_for_update().first()
    if record is None:
        return _error_404()
        
    data = request.get_json(silent=True) or {}
    final_hs_code = data.get("final_hs_code")
    if not final_hs_code:
        return jsonify({"error": "Missing required field: final_hs_code"}), 400
        
    # Phase 1.5 Fix: Validate lock ownership if locked
    if record.status == "locked" and record.locked_by:
        operator_id = request.headers.get("X-Operator-Id")
        if record.locked_by != operator_id:
            return jsonify({
                "error": "Forbidden: Classification is locked by another operator",
                "locked_by": record.locked_by
            }), 403
            
    record.final_hs_code = final_hs_code
    record.reviewed_at = datetime.utcnow()
    record.status = "reviewed"
    record.review_required = False
    record.locked_by = None
    
    if data.get("review_comment"):
        record.review_comment = data.get("review_comment")
    if data.get("reviewed_by"):    
        record.reviewed_by = data.get("reviewed_by")
        
    db.session.add(record)
    
    # Product同期処理（存在する場合）
    from app.models import Product
    if record.product_id:
        product = db.session.get(Product, record.product_id)
        if product:
            product.hs_base6 = final_hs_code
            product.active_classification_id = record.id
            db.session.add(product)
            
    db.session.commit()
    
    trace_id = request.headers.get("X-Trace-Id") or record.trace_id
    log_event(
        trace_id=trace_id, 
        event="hs.review.finalized", 
        target_type="hs_classification", 
        target_id=record.id,
        final_hs_code=final_hs_code
    )
    return jsonify(_serialize(record)), 200


@bp.post("/hs-classifications/<int:id>:reopen")
@require_api_key
def reopen_hs_classification(id: int) -> Tuple[Response, int]:
    record: Optional[HSClassification] = db.session.query(HSClassification).filter_by(id=id).with_for_update().first()
    if record is None:
        return _error_404()
        
    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    if not reason:
        return jsonify({"error": "Missing required field: reason"}), 400
        
    # Check if a Shipment exists using this record's product
    from app.models import Product, Shipment, ShipmentLine
    
    product_id = record.product_id
    if product_id:
        # Check shipment references
        has_shipment = db.session.query(Shipment.id).join(ShipmentLine).filter(  # type: ignore
            ShipmentLine.product_id == product_id,
            Shipment.status != "canceled"
        ).first()
        
        if has_shipment:
            return jsonify({
                "error": "Cannot reopen a classification linked to an active Shipment.",
                "shipment_id": has_shipment[0]
            }), 409
            
        product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
        if product:
            product.status = "ready" # Trigger validation queueing equivalent
            product.active_classification_id = None
            db.session.add(product)
            
            # Dispatch HS classify job manually since validate_product might be skipped
            from app.models import Job
            import uuid
            trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
            job = Job(
                type="hs_classify",
                status="queued",
                payload_json={
                    "product_id": product.id,
                    "event_type": "PRODUCT_REOPENED",
                    "reason": reason
                },
                trace_id=trace_id
            )
            db.session.add(job)
            
    record.status = "superseded"
    db.session.add(record)
    
    db.session.commit()
    
    trace_id = request.headers.get("X-Trace-Id") or record.trace_id
    log_event(
        trace_id=trace_id,
        event="hs.review.reopened",
        target_type="hs_classification",
        target_id=record.id,
        reason=reason
    )
    
    return jsonify(_serialize(record)), 200
    return jsonify(_serialize(record)), 200
