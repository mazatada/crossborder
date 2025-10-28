from . import register

@register("clearance_pack")
def handle(payload: dict, *, job_id: int, trace_id: str):
    required = payload.get("required_uom")
    invoice = payload.get("invoice_uom")
    return {
        "artifacts": [
            {"type": "commercial_invoice", "media_id": "dev:ci"},
            {"type": "packing_list", "media_id": "dev:pl"},
        ],
        "uom_check": {"required": required, "invoice": invoice, "valid": (required == invoice)},
        "trace_id": trace_id,
    }
