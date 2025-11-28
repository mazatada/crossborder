from . import register

@register("pn_submit")
def handle(payload: dict, *, job_id: int, trace_id: str):
    required_fields = ["traceId", "product", "logistics", "importer", "consignee"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        from app.jobs import cli
        raise cli.NonRetriableError(f"missing fields: {','.join(missing)}")

    return {"submitted": True, "receipt_media_id": "dev:pn-receipt", "trace_id": trace_id}
