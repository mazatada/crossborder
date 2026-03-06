# app/jobs/handlers/generate_docs.py
"""Job handler for document generation (Phase 2).

Generates CSV/JSON line-item data for a validated Shipment, creates
DocumentExport records, and transitions the Shipment to 'completed'.

On failure, rolls back the Shipment to 'failed' and logs the error to
audit_events – preventing zombie 'generating' states.
"""
from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime

from . import register

logger = logging.getLogger(__name__)


@register("generate_docs")
def handle(payload: dict, *, job_id: int, trace_id: str) -> dict:
    """Generate export documents for a shipment."""
    from app.db import db
    from app.models import Shipment, ShipmentLine, DocumentExport
    from app.audit import log_event

    shipment_id = payload.get("shipment_id")
    if not shipment_id:
        raise ValueError("Missing shipment_id in job payload")

    shipment = db.session.query(Shipment).get(shipment_id)
    if not shipment:
        raise ValueError(f"Shipment {shipment_id} not found")

    try:
        # ── Gather line data ──
        lines = db.session.query(ShipmentLine).filter_by(shipment_id=shipment_id).all()

        # ── Build invoice line items ──
        invoice_lines = []
        for sl in lines:
            invoice_lines.append(
                {
                    "line_id": sl.id,
                    "product_id": sl.product_id,
                    "description": sl.description_en or "",
                    "origin_country": sl.origin_country,
                    "hs_code": sl.hs_base6 or "",
                    "country_specific_code": sl.country_specific_code or "",
                    "quantity": sl.qty,
                    "unit_price": sl.unit_price,
                    "currency": sl.currency,
                    "line_value": sl.line_value,
                    "weight_g": sl.line_weight_g,
                }
            )

        # ── Build packing list ──
        packing_data = {
            "shipment_id": shipment.id,
            "destination_country": shipment.destination_country,
            "shipping_mode": shipment.shipping_mode,
            "incoterm": shipment.incoterm,
            "total_weight_g": shipment.total_weight_g,
            "total_value": shipment.total_value,
            "currency": shipment.currency,
            "lines": [
                {
                    "product_id": sl.product_id,
                    "description": sl.description_en or "",
                    "quantity": sl.qty,
                    "weight_g": sl.line_weight_g,
                }
                for sl in lines
            ],
        }

        # ── Write output files ──
        export_dir = os.getenv("EXPORT_DIR", "/tmp/exports")
        os.makedirs(export_dir, exist_ok=True)

        invoice_path = os.path.join(export_dir, f"shipment_{shipment_id}_invoice.json")
        with open(invoice_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "shipment_id": shipment.id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "lines": invoice_lines,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        packing_path = os.path.join(
            export_dir, f"shipment_{shipment_id}_packing_list.json"
        )
        with open(packing_path, "w", encoding="utf-8") as f:
            json.dump(packing_data, f, ensure_ascii=False, indent=2)

        # ── Create DocumentExport records ──
        invoice_export = DocumentExport(
            shipment_id=shipment_id,
            type="invoice",
            format="json",
            s3_key=invoice_path,
            storage_url=invoice_path,
        )
        packing_export = DocumentExport(
            shipment_id=shipment_id,
            type="packing_list",
            format="json",
            s3_key=packing_path,
            storage_url=packing_path,
        )
        db.session.add(invoice_export)
        db.session.add(packing_export)

        # ── Transition shipment to completed ──
        shipment.status = "completed"
        db.session.commit()

        log_event(
            trace_id=trace_id,
            event="shipment.docs_generated",
            target_type="shipment",
            target_id=shipment_id,
        )

        logger.info(
            f"[generate_docs] Shipment {shipment_id} docs generated successfully."
        )

        return {
            "exports": [
                {"type": "invoice", "path": invoice_path},
                {"type": "packing_list", "path": packing_path},
            ],
            "trace_id": trace_id,
        }

    except Exception as e:
        logger.error(
            f"[generate_docs] Failed for shipment {shipment_id}: {e}\n{traceback.format_exc()}"
        )
        # ── Rollback: prevent zombie 'generating' state ──
        try:
            db.session.rollback()
            shipment_retry = db.session.query(Shipment).get(shipment_id)
            if shipment_retry and shipment_retry.status == "generating":
                shipment_retry.status = "failed"
                db.session.commit()

            log_event(
                trace_id=trace_id,
                event="shipment.docs_generation_failed",
                target_type="shipment",
                target_id=shipment_id,
                error=str(e),
            )
        except Exception as rollback_err:
            logger.error(f"[generate_docs] Rollback also failed: {rollback_err}")

        raise
