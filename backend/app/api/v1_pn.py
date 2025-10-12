from flask import Blueprint, request, jsonify
from ..util.validate import require_json, ensure_required
from ..models import Job, Artifact, PNSubmission, Audit
from ..db import db
import uuid, hashlib, json
from datetime import datetime, timedelta

bp = Blueprint("pn", __name__)

def deadline_violation(mode:str, arrival:str) -> bool:
    # very simple deadline check
    try:
        arrival_dt = datetime.fromisoformat(arrival)
    except: return True
    now = datetime.utcnow()
    delta = arrival_dt - now
    if mode=="sea": return delta.total_seconds() < 24*3600
    return delta.total_seconds() < 2*3600  # air/express
       
@bp.post("/fda/prior-notice")
@require_json
def pn_submit():
    data = request.get_json()
    product = data.get("product",{})
    logistics = data.get("logistics",{})
    importer = data.get("importer",{})
    consignee = data.get("consignee",{})
    label_media_id = data.get("label_media_id")
    missing = ensure_required({
        "product.description": product.get("description"),
        "product.origin_country": product.get("origin_country"),
        "logistics.mode": logistics.get("mode"),
        "logistics.port_of_entry": logistics.get("port_of_entry"),
        "logistics.arrival_date": logistics.get("arrival_date"),
        "importer.name": importer.get("name"),
        "consignee.name": consignee.get("name"),
        "label_media_id": label_media_id
    })
    if missing:
        return jsonify({"pn_required": True, "status":"failed","errors":missing}), 400
    if deadline_violation(logistics["mode"], logistics["arrival_date"]):
        return jsonify({"pn_required": True, "status":"failed","errors":["deadline_passed"]}), 400
    job_id = f"JOB-{uuid.uuid4().hex[:12]}"
    job = Job(id=job_id, type="pn", status="queued", trace_id=data.get("traceId"))
    db.session.add(job); db.session.commit()
    # immediate simulate submit
    job.status="submitted"; db.session.commit()
    receipt = f"PN-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    payload_hash = hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    pn = PNSubmission(trace_id=data.get("traceId"), receipt_no=receipt, status="submitted", payload=data)
    db.session.add(pn)
    art = Artifact(job_id=job.id, type="pn_receipt", media_id=receipt, sha256=payload_hash, size=len(payload_hash))
    db.session.add(art)
    audit = Audit(trace_id=data.get("traceId"), event="PN_SUBMITTED", payload={"receipt_no":receipt})
    db.session.add(audit); db.session.commit()
    return jsonify({"job_id": job_id}), 202
