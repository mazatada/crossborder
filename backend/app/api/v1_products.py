import uuid
from typing import Tuple, Any, Dict, Optional

from flask import Blueprint, jsonify, request, Response
from app.auth import require_api_key
from app.db import db
from app.models import Product
from app.audit import log_event

bp = Blueprint("v1_products", __name__, url_prefix="/v1")


def _error_404() -> Tuple[Response, int]:
    return (
        jsonify(
            {
                "error": {
                    "class": "not_found",
                    "message": "Product not found",
                    "field": "id",
                    "severity": "block",
                }
            }
        ),
        404,
    )


def _serialize(record: Product) -> Dict[str, Any]:
    res = {
        "id": record.id,
        "external_ref": record.external_ref,
        "title": record.title,
        "description_en": record.description_en,
        "origin_country": record.origin_country,
        "is_food": record.is_food,
        "processing_state": record.processing_state,
        "physical_form": record.physical_form,
        "unit_weight_g": record.unit_weight_g,
        "dimensions_mm": record.dimensions_mm,
        "shelf_life_days": record.shelf_life_days,
        "packaging": record.packaging,
        "animal_derived_flags": record.animal_derived_flags,
        "hs_base6": record.hs_base6,
        "active_classification_id": record.active_classification_id,
        "country_specific_codes": record.country_specific_codes,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
    
    from sqlalchemy.orm.attributes import instance_state
    state = instance_state(record)
    if "active_classification" in state.dict:
        if record.active_classification:
            res["active_classification"] = {
                "id": str(record.active_classification.id),
                "final_hs_code": record.active_classification.final_hs_code,
                "status": record.active_classification.status
            }
        else:
            res["active_classification"] = None
            
    return res


@bp.post("/products")
@require_api_key
def create_product() -> Tuple[Response, int]:
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"error": "Missing required field: title"}), 400

    is_food = data.get("is_food", False)
    if not isinstance(is_food, bool):
        return jsonify({"error": "Invalid field: is_food must be a boolean"}), 400
        
    for num_field in ["unit_weight_g", "shelf_life_days"]:
        val = data.get(num_field)
        if val is not None and not isinstance(val, (int, float)):
            return jsonify({"error": f"Invalid field: {num_field} must be a number"}), 400

    record = Product(
        title=title,
        external_ref=data.get("external_ref"),
        description_en=data.get("description_en"),
        origin_country=data.get("origin_country", "XX"),
        is_food=is_food,
        processing_state=data.get("processing_state"),
        physical_form=data.get("physical_form"),
        unit_weight_g=data.get("unit_weight_g"),
        dimensions_mm=data.get("dimensions_mm"),
        shelf_life_days=data.get("shelf_life_days"),
        packaging=data.get("packaging"),
        animal_derived_flags=data.get("animal_derived_flags"),
        status="draft"
    )

    db.session.add(record)
    db.session.commit()

    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    log_event(
        trace_id=trace_id,
        event="product.created",
        target_type="product",
        target_id=record.id,
    )

    return jsonify(_serialize(record)), 201


@bp.put("/products/<int:id>")
@require_api_key
def update_product(id: int) -> Tuple[Response, int]:
    record: Optional[Product] = db.session.get(Product, id)
    if record is None:
        return _error_404()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    updatable_fields = [
        "title", "external_ref", "description_en", "origin_country", "is_food",
        "processing_state", "physical_form", "unit_weight_g", "dimensions_mm",
        "shelf_life_days", "packaging", "animal_derived_flags", "status"
    ]
    
    # 厳密な型チェック (Strict Validation)
    if "is_food" in data and not isinstance(data["is_food"], bool):
        return jsonify({"error": "Invalid field: is_food must be a boolean"}), 400
    for num_field in ["unit_weight_g", "shelf_life_days"]:
        if num_field in data and data[num_field] is not None and not isinstance(data[num_field], (int, float)):
            return jsonify({"error": f"Invalid field: {num_field} must be a number"}), 400
    
    # 運用中の破壊的変更をガード (Phase 1 hotfix)
    critical_fields = ["is_food", "unit_weight_g", "processing_state", "physical_form", "origin_country"]
    if record.status != "draft":
        for field in critical_fields:
            if field in data and getattr(record, field) != data[field]:
                return jsonify({
                    "error": f"Cannot modify critical field '{field}' when product status is '{record.status}'"
                }), 409

    for field in updatable_fields:
        if field in data:
            setattr(record, field, data[field])

    db.session.add(record)
    db.session.commit()

    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    log_event(
        trace_id=trace_id,
        event="product.updated",
        target_type="product",
        target_id=record.id,
    )

    return jsonify(_serialize(record)), 200


@bp.get("/products")
@require_api_key
def get_products() -> Tuple[Response, int]:
    status = request.args.get("status")
    q = db.session.query(Product)
    if status:
        q = q.filter(Product.status == status)  # type: ignore

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    if limit > 200:
        limit = 200

    include_str = request.args.get("include")
    if include_str:
        includes = include_str.split(",")
        from sqlalchemy.orm import selectinload
        if "hs" in includes:
            q = q.options(selectinload(Product.active_classification))

    total = q.count()

    records = q.order_by(Product.id.desc()).offset((page - 1) * limit).limit(limit).all()  # type: ignore

    return jsonify({
        "data": [_serialize(r) for r in records],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit
        }
    }), 200


@bp.post("/products/<int:id>/validate")
@require_api_key
def validate_product(id: int) -> Tuple[Response, int]:
    record: Optional[Product] = db.session.get(Product, id)
    if record is None:
        return _error_404()

    errors = []
    # 必須（出荷ブロッカー）
    required_fields = ["description_en", "origin_country", "processing_state", "physical_form", "unit_weight_g"]
    for field in required_fields:
        if not getattr(record, field) and getattr(record, field) is not False: # allow is_food=False
             errors.append({
                 "field": field,
                 "message": f"Missing required field: {field}",
                 "severity": "block"
             })

    # 準必須（欠けたらレビュー）
    warnings = []
    if record.is_food:
        if record.shelf_life_days is None:
            warnings.append({
                "field": "shelf_life_days",
                "message": "Highly recommended for food products",
                "severity": "review"
            })
        if record.animal_derived_flags is None:
             warnings.append({
                 "field": "animal_derived_flags",
                 "message": "Animal derived flags are required to determine food regulations",
                 "severity": "review"
             })

    response_data = {
        "valid": len(errors) == 0,
        "product_id": record.id,
        "errors": errors,
        "warnings": warnings
    }

    if len(errors) == 0 and record.status == "draft":
        record.status = "ready"
        db.session.add(record)
        
        # Enqueue HS Classification task (Phase 1.5)
        from app.models import Job
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        job = Job(
            type="hs_classify",
            status="queued",
            payload_json={
                "product_id": record.id,
                "event_type": "PRODUCT_READY"
            },
            trace_id=trace_id
        )
        db.session.add(job)
        
        db.session.commit()

    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    log_event(
        trace_id=trace_id,
        event="product.validated",
        target_type="product",
        target_id=record.id,
        valid=len(errors) == 0,
    )

    return jsonify(response_data), 200
