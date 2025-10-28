from . import register

@register("pn_submit")
def handle(payload: dict, *, job_id: int, trace_id: str):
    return {"submitted": True, "receipt_media_id": "dev:pn-receipt", "trace_id": trace_id}
