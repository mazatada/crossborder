# backend/app/jobs/handlers/echo.py
def handle(payload: dict, *, job_id: int, trace_id: str) -> dict:
    return {"ok": True, "job_id": job_id, "trace_id": trace_id, "echo": payload}
