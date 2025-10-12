from .db import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256))
    category = db.Column(db.String(64))
    data_json = db.Column(db.JSON)  # full product/logistics/valuation/pn_fields/media
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HSOverride(db.Model):
    __tablename__ = "hs_overrides"
    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(64), index=True)
    hs_code = db.Column(db.String(16))
    reason = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PNSubmission(db.Model):
    __tablename__ = "pn_submissions"
    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(64), index=True)
    receipt_no = db.Column(db.String(64))
    status = db.Column(db.String(32))
    payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.String(40), primary_key=True)
    type = db.Column(db.String(32))  # pn|pack
    status = db.Column(db.String(32))  # queued|validating|submitted|failed|rendering|completed
    trace_id = db.Column(db.String(64), index=True)
    error = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Artifact(db.Model):
    __tablename__ = "artifacts"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(40), db.ForeignKey("jobs.id"))
    type = db.Column(db.String(32))  # pn_receipt|clearance_zip
    media_id = db.Column(db.String(128))
    sha256 = db.Column(db.String(128))
    size = db.Column(db.Integer)

class Audit(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(64), index=True)
    event = db.Column(db.String(64))  # HS_CLASSIFIED / PN_SUBMITTED / DOCS_PACKAGED / ...
    payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
