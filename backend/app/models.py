# backend/app/models.py
from datetime import datetime
from .db import db

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # ← ここが超重要
    type = db.Column(db.String(16), nullable=False)         # "pack" | "pn" | etc
    status = db.Column(db.String(16), nullable=False, index=True)
    trace_id = db.Column(db.String(64), index=True)
    error = db.Column(db.JSON, nullable=True)

    # 追加済みのカラム（migrations で作ったやつ）
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_run_at = db.Column(db.DateTime, nullable=True)
    payload_json = db.Column(db.JSON, nullable=True)
    result_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class MediaBlob(db.Model):
    __tablename__ = "media_blobs"
    media_id = db.Column(db.String(128), primary_key=True)
    sha256 = db.Column(db.String(64), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    mime = db.Column(db.String(64), nullable=False, default="application/octet-stream")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

Artifact = MediaBlob

class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id = db.Column(db.String(64), index=True, nullable=False)
    event = db.Column(db.String(64), nullable=False)
    payload = db.Column(db.JSON, nullable=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class PNSubmission(db.Model):
    __tablename__ = "pn_submissions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id = db.Column(db.String(64), index=True, nullable=False)
    product = db.Column(db.JSON, nullable=False)
    logistics = db.Column(db.JSON, nullable=False)
    importer = db.Column(db.JSON, nullable=False)
    consignee = db.Column(db.JSON, nullable=False)
    label_media_id = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class DocumentPackage(db.Model):
    __tablename__ = "document_packages"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id = db.Column(db.String(64), index=True, nullable=False)
    hs_code = db.Column(db.String(16), nullable=False)
    required_uom = db.Column(db.String(8), nullable=False)
    invoice_uom = db.Column(db.String(8), nullable=False)
    invoice_payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
