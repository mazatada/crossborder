from flask import Blueprint, request, jsonify
from ..util.validate import require_json
from ..models import Job, AuditEvent, MediaBlob  # 必要なものだけに可
from ..db import db
import uuid, hashlib, json
bp = Blueprint("docs", __name__)

@bp.post("/docs/clearance-pack")
@require_json
def pack():
    data = request.get_json()
    # Minimal checks (UoM例)
    hs_uom = data.get("required_uom","kg")
    invoice_uom = data.get("invoice_uom","kg")
    if hs_uom != invoice_uom:
        return jsonify({"error":{"class":"invalid_uom","message":"HS requires %s, invoice uses %s"%(hs_uom, invoice_uom),"field":"invoice_uom","severity":"block"}}), 400
    job_id = f"JOB-{uuid.uuid4().hex[:12]}"
    job = Job(id=job_id, type="pack", status="rendering", trace_id=data.get("traceId"))
    db.session.add(job); db.session.commit()
    # simulate artifact
    manifest = {"traceId": data.get("traceId"), "hs_primary": data.get("hs_code"), "required_uom": hs_uom}
    sha = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    art = Artifact(job_id=job_id, type="clearance_zip", media_id=f"CLEARANCE_{data.get('traceId')}.zip", sha256=sha, size=1024)
    db.session.add(art); db.session.add(Audit(trace_id=data.get("traceId"), event="DOCS_PACKAGED", payload={"sha256":sha}))
    job.status="completed"; db.session.commit()
    return jsonify({"job_id": job_id}), 202
