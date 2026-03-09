# app/api/v1_shipments.py
"""Shipment domain API – Phase 2

Endpoints:
  POST   /v1/shipments                          – create shipment + lines (with product snapshot)
  GET    /v1/shipments                           – list shipments (paginated)
  POST   /v1/shipments/<id>/validate             – validate shipment readiness
  POST   /v1/shipments/<id>/generate-docs        – enqueue document generation job
  GET    /v1/shipments/<id>/exports              – list generated exports
  GET    /v1/shipments/<id>/exports/<eid>/download – redirect to presigned download URL
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from app.db import db
from app.auth import require_api_key
from app.middleware.idempotency import require_idempotency_key
from app.audit import log_event
from app.logging_conf import get_trace_id

bp = Blueprint("v1_shipments", __name__)


def _serialize_shipment(s) -> dict:  # type: ignore
    return {
        "id": s.id,
        "order_ref": s.order_ref,
        "trace_id": s.trace_id,
        "destination_country": s.destination_country,
        "shipping_mode": s.shipping_mode,
        "incoterm": s.incoterm,
        "currency": s.currency,
        "total_value": float(s.total_value) if s.total_value is not None else 0.0,
        "total_weight_g": s.total_weight_g,
        "status": s.status,
        "validation_errors": s.validation_errors,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _serialize_line(line) -> dict:  # type: ignore
    return {
        "id": line.id,
        "product_id": line.product_id,
        "qty": line.qty,
        "unit_price": float(line.unit_price) if line.unit_price is not None else 0.0,
        "currency": line.currency,
        "line_value": float(line.line_value) if line.line_value is not None else 0.0,
        "line_weight_g": line.line_weight_g,
        "hs_base6": line.hs_base6,
        "country_specific_code": line.country_specific_code,
        "origin_country": line.origin_country,
        "description_en": line.description_en,
    }


# ──────────────── POST /v1/shipments ────────────────
@bp.route("/v1/shipments", methods=["POST"])
@require_api_key
@require_idempotency_key
def create_shipment():
    from app.models import Shipment, ShipmentLine, Product

    data = request.get_json(silent=True) or {}
    required = ["destination_country", "shipping_mode", "lines"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    lines_data = data["lines"]
    if not isinstance(lines_data, list) or len(lines_data) == 0:
        return jsonify({"error": "lines must be a non-empty array"}), 400

    # ── Atomic product validation (bulk SELECT) ──
    product_ids = [
        line.get("product_id") for line in lines_data if line.get("product_id")
    ]
    if not product_ids:
        return jsonify({"error": "Each line must include a product_id"}), 400

    products = (
        db.session.query(Product)
        .filter(Product.id.in_(product_ids))  # type: ignore
        .all()
    )
    product_map = {p.id: p for p in products}

    # Check all products exist
    missing_ids = set(product_ids) - set(product_map.keys())
    if missing_ids:
        return (
            jsonify({"error": f"Products not found: {sorted(missing_ids)}"}),
            400,
        )

    # Check all products are in 'ready' status
    not_ready = [pid for pid, p in product_map.items() if p.status != "ready"]
    if not_ready:
        return (
            jsonify(
                {
                    "error": "All products must be in 'ready' status",
                    "not_ready_product_ids": not_ready,
                }
            ),
            400,
        )

    trace_id = get_trace_id()
    shipment = Shipment(
        order_ref=data.get("order_ref"),
        trace_id=trace_id,
        destination_country=data["destination_country"],
        shipping_mode=data["shipping_mode"],
        incoterm=data.get("incoterm", "DDP"),
        currency=data.get("currency", "USD"),
    )
    db.session.add(shipment)
    db.session.flush()  # get shipment.id

    total_value = 0.0
    total_weight_g = 0
    created_lines = []

    for line_data in lines_data:
        pid = line_data["product_id"]
        product = product_map[pid]
        qty = int(line_data.get("qty", 1))
        unit_price = float(line_data.get("unit_price", 0.0))
        currency = line_data.get("currency", data.get("currency", "USD"))
        weight_per_unit = product.unit_weight_g or 0
        line_weight = weight_per_unit * qty
        line_value = unit_price * qty

        # Build product snapshot for audit immutability
        snapshot = {
            "id": product.id,
            "title": product.title,
            "origin_country": product.origin_country,
            "is_food": product.is_food,
            "hs_base6": product.hs_base6,
            "unit_weight_g": product.unit_weight_g,
            "description_en": product.description_en,
        }

        sl = ShipmentLine(
            shipment_id=shipment.id,
            product_id=pid,
            qty=qty,
            unit_price=unit_price,
            currency=currency,
            line_value=line_value,
            line_weight_g=line_weight,
            hs_base6=product.hs_base6,
            country_specific_code=(product.country_specific_codes or {}).get(
                data["destination_country"]
            ),
            origin_country=product.origin_country,
            description_en=product.description_en,
            product_snapshot=snapshot,
        )
        db.session.add(sl)
        created_lines.append(sl)
        total_value += line_value
        total_weight_g += line_weight

    shipment.total_value = total_value
    shipment.total_weight_g = total_weight_g
    db.session.commit()

    log_event(
        trace_id=trace_id,
        event="shipment.created",
        target_type="shipment",
        target_id=shipment.id,
    )

    result = _serialize_shipment(shipment)
    result["lines"] = [_serialize_line(sl) for sl in created_lines]
    return jsonify(result), 201


# ──────────────── GET /v1/shipments ────────────────
@bp.route("/v1/shipments", methods=["GET"])
@require_api_key
def list_shipments():
    from app.models import Shipment

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status_filter = request.args.get("status")

    query = db.session.query(Shipment)
    if status_filter:
        query = query.filter(Shipment.status == status_filter)  # type: ignore
    query = query.order_by(Shipment.created_at.desc())  # type: ignore
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        {
            "items": [_serialize_shipment(s) for s in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


# ──────────────── POST /v1/shipments/<id>/validate ────────────────
@bp.route("/v1/shipments/<int:shipment_id>/validate", methods=["POST"])
@require_api_key
def validate_shipment(shipment_id: int):
    from app.models import Shipment, ShipmentLine, Product, HSClassification

    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({"error": "Shipment not found"}), 404
    if shipment.status not in ("draft",):
        return (
            jsonify(
                {"error": f"Cannot validate shipment in '{shipment.status}' status"}
            ),
            409,
        )

    lines = db.session.query(ShipmentLine).filter_by(shipment_id=shipment_id).all()
    if not lines:
        return jsonify({"error": "Shipment has no lines"}), 400

    errors = []
    product_ids = [sl.product_id for sl in lines if sl.product_id]
    # Eager load products + classifications to avoid N+1
    products = (
        db.session.query(Product)
        .filter(Product.id.in_(product_ids))  # type: ignore
        .all()
    )
    product_map = {p.id: p for p in products}

    for sl in lines:
        pid = sl.product_id
        product = product_map.get(pid)  # type: ignore
        if not product:
            errors.append({"line_id": sl.id, "error": f"Product {pid} not found"})
            continue
        if product.status != "ready":
            errors.append(
                {
                    "line_id": sl.id,
                    "product_id": pid,
                    "error": "Product not in 'ready' status",
                }
            )

        # Check HS classification is finalized
        if product.active_classification_id:
            hsc = db.session.query(HSClassification).get(
                product.active_classification_id
            )
            if hsc and hsc.status not in ("locked", "reviewed"):
                errors.append(
                    {
                        "line_id": sl.id,
                        "product_id": pid,
                        "error": f"HS classification not finalized (status={hsc.status})",
                    }
                )
        else:
            errors.append(
                {
                    "line_id": sl.id,
                    "product_id": pid,
                    "error": "No active HS classification",
                }
            )

        # FDA check: food products need PN confirmation number
        if product.is_food:
            # Check if PN submission exists for this product/trace
            from app.models import PNSubmission

            pn = (
                db.session.query(PNSubmission)
                .filter(PNSubmission.trace_id.like(f"%product-{pid}%"))  # type: ignore
                .first()
            )
            if not pn:
                errors.append(
                    {
                        "line_id": sl.id,
                        "product_id": pid,
                        "error": "Food product requires FDA Prior Notice (PN) submission",
                    }
                )

    if errors:
        shipment.validation_errors = errors
        db.session.commit()
        return jsonify({"valid": False, "errors": errors}), 422

    # Validation passed → transition to validated
    shipment.status = "validated"
    shipment.validation_errors = None
    db.session.commit()

    log_event(
        trace_id=get_trace_id(),
        event="shipment.validated",
        target_type="shipment",
        target_id=shipment_id,
    )

    return jsonify({"valid": True, "shipment": _serialize_shipment(shipment)})


# ──────────────── POST /v1/shipments/<id>/generate-docs ────────────────
@bp.route("/v1/shipments/<int:shipment_id>/generate-docs", methods=["POST"])
@require_api_key
def generate_docs(shipment_id: int):
    from app.models import Shipment, Job

    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({"error": "Shipment not found"}), 404

    if shipment.status == "generating":
        return jsonify({"error": "Document generation already in progress"}), 409
    if shipment.status != "validated":
        return (
            jsonify(
                {
                    "error": f"Shipment must be 'validated' to generate docs (current: '{shipment.status}')"
                }
            ),
            409,
        )

    # Transition to generating (state machine guards double-fire)
    shipment.status = "generating"

    # Enqueue async job
    trace_id = get_trace_id()
    job = Job(
        type="generate_docs",
        status="queued",
        trace_id=trace_id,
        payload_json={"shipment_id": shipment_id},
    )
    db.session.add(job)
    db.session.commit()

    log_event(
        trace_id=trace_id,
        event="shipment.generate_docs_queued",
        target_type="shipment",
        target_id=shipment_id,
    )

    return (
        jsonify({"job_id": job.id, "shipment_id": shipment_id, "status": "generating"}),
        202,
    )


# ──────────────── GET /v1/shipments/<id>/exports ────────────────
@bp.route("/v1/shipments/<int:shipment_id>/exports", methods=["GET"])
@require_api_key
def list_exports(shipment_id: int):
    from app.models import Shipment, DocumentExport

    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({"error": "Shipment not found"}), 404

    exports = (
        db.session.query(DocumentExport)
        .filter_by(shipment_id=shipment_id)
        .order_by(DocumentExport.created_at.desc())  # type: ignore
        .all()
    )

    items = []
    for exp in exports:
        items.append(
            {
                "id": exp.id,
                "type": exp.type,
                "format": exp.format,
                "schema_version": exp.schema_version,
                "download_url": f"/v1/shipments/{shipment_id}/exports/{exp.id}/download",
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
            }
        )

    return jsonify({"shipment_id": shipment_id, "exports": items})


# ──────────────── GET /v1/shipments/<id>/exports/<eid>/download ────────────────
@bp.route(
    "/v1/shipments/<int:shipment_id>/exports/<int:export_id>/download",
    methods=["GET"],
)
@require_api_key
def download_export(shipment_id: int, export_id: int):
    from flask import redirect
    from app.models import DocumentExport

    export = (
        db.session.query(DocumentExport)
        .filter_by(id=export_id, shipment_id=shipment_id)
        .first()
    )
    if not export:
        return jsonify({"error": "Export not found"}), 404

    log_event(
        trace_id=get_trace_id(),
        event="export.downloaded",
        target_type="document_export",
        target_id=export_id,
    )

    # In production: generate S3 presigned URL here
    # For MVP, return the storage_url or s3_key as a redirect
    url = export.storage_url or export.s3_key
    if not url:
        return jsonify({"error": "Export file not yet available"}), 404

    return redirect(url)
