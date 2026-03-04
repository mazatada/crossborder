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
        .filter_by(product_id=product_id)
        .order_by(HSClassification.created_at.desc())  # type: ignore
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
        .filter_by(trace_id=record.trace_id, type="clearance_pack")
        .order_by(Job.created_at.desc())  # type: ignore
        .first()
    )
    pn_job = (
        db.session.query(Job)
        .filter_by(trace_id=record.trace_id, type="pn_submit")
        .order_by(Job.created_at.desc())  # type: ignore
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


@bp.post("/evaluate")
@require_api_key
def evaluate_compliance() -> Tuple[Response, int]:
    from flask import request
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    destination_country = data.get("destination_country")
    shipping_mode = data.get("shipping_mode")
    incoterm = data.get("incoterm")
    
    if getattr(product_id, "__class__", None) not in (int, str) or not isinstance(destination_country, str):
        return jsonify({"error": "Missing required fields: product_id, destination_country"}), 400
        
    # Enum / Format 厳格バリデーション (Phase 1 hotfix)
    if len(destination_country) != 2 or not destination_country.isalpha():
        return jsonify({"error": "Invalid field: destination_country must be a 2-letter ISO code"}), 400
    destination_country = destination_country.upper()
    
    if shipping_mode and shipping_mode not in ["postal", "courier"]:
        return jsonify({"error": "Invalid field: shipping_mode must be 'postal' or 'courier'"}), 400
        
    from app.models import Product
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    allowed = True
    block_reasons = []
    required_codes: list[str] = []
    required_fields: list[str] = []
    notes = []
    
    # 簡易的なハードコードルール評価（MVPフェーズ用）
    if destination_country.upper() == "US":
        if product.is_food:
            notes.append("FDA Prior Notice is required for US food imports")
            required_codes.extend(["fda_product_code", "fda_facility_registration_number"])
            if shipping_mode == "postal":
                notes.append("Postal shipping for food to US may experience delays")
    
    # 例: 特定のインコタームズや配送モードの組み合わせブロック
    if incoterm == "DDP" and shipping_mode == "postal":
         allowed = False
         block_reasons.append("DDP is not generally supported for postal shipping")
         
    # 英国(GB)やEUへのDDPでの税務要件
    if destination_country.upper() in ["GB", "FR", "DE", "IT", "ES", "NL"] and incoterm == "DDP":
        notes.append(f"VAT registration may be required for DDP to {destination_country.upper()}")
        required_codes.append("vat_number")

    return jsonify({
        "allowed": allowed,
        "block_reasons": block_reasons,
        "required_codes": required_codes,
        "required_fields": required_fields,
        "notes": notes
    }), 200
