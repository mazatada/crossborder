from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import UniqueConstraint
from .db import db, Base


class Job(Base):
    __tablename__ = "jobs"
    id: int = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    type: str = db.Column(db.String(16), nullable=False)  # type: ignore
    status: str = db.Column(db.String(16), nullable=False, index=True)  # type: ignore
    trace_id: Optional[str] = db.Column(db.String(64), index=True)  # type: ignore
    error: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    attempts: int = db.Column(db.Integer, nullable=False, default=0)  # type: ignore
    next_run_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)  # type: ignore
    payload_json: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    result_json: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # type: ignore


class MediaBlob(Base):
    __tablename__ = "media_blobs"
    media_id: str = db.Column(db.String(128), primary_key=True)  # type: ignore
    sha256: str = db.Column(db.String(64), nullable=False)  # type: ignore
    size: int = db.Column(db.Integer, nullable=False)  # type: ignore
    mime: str = db.Column(db.String(64), nullable=False, default="application/octet-stream")  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


Artifact = MediaBlob


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    event: str = db.Column(db.String(64), nullable=False)  # type: ignore
    payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    ts: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


class PNSubmission(Base):
    __tablename__ = "pn_submissions"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    product: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    logistics: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    importer: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    consignee: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    label_media_id: Optional[str] = db.Column(db.String(128), nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


class DocumentPackage(Base):
    __tablename__ = "document_packages"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    hs_code: str = db.Column(db.String(16), nullable=False)  # type: ignore
    required_uom: str = db.Column(db.String(8), nullable=False)  # type: ignore
    invoice_uom: str = db.Column(db.String(8), nullable=False)  # type: ignore
    invoice_payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    url: str = db.Column(db.String(512), nullable=False)  # type: ignore
    secret: str = db.Column(db.String(128), nullable=False)  # type: ignore
    events: List[str] = db.Column(db.JSON, nullable=False)  # type: ignore
    active: bool = db.Column(db.Boolean, default=True, nullable=False)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # type: ignore


class OrderStatus(Base):
    __tablename__ = "order_statuses"
    __table_args__ = (UniqueConstraint("order_id", "status", name="uq_order_status"),)
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    order_id: str = db.Column(db.String(128), nullable=False, index=True)  # type: ignore
    status: str = db.Column(db.String(32), nullable=False)  # type: ignore
    ts: datetime = db.Column(db.DateTime, nullable=False)  # type: ignore
    customer_region: Optional[str] = db.Column(db.String(64), nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


class WebhookDLQ(Base):
    __tablename__ = "webhook_dlq"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    webhook_id: int = db.Column(
        db.Integer, db.ForeignKey("webhook_endpoints.id"), nullable=False
    )  # type: ignore
    event_type: str = db.Column(db.String(64), nullable=False)  # type: ignore
    payload: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    trace_id: Optional[str] = db.Column(db.String(64), index=True, nullable=True)  # type: ignore
    attempts: int = db.Column(db.Integer, nullable=False, default=0)  # type: ignore
    last_error: Optional[str] = db.Column(db.Text, nullable=True)  # type: ignore
    last_status_code: Optional[int] = db.Column(db.Integer, nullable=True)  # type: ignore
    replayed: bool = db.Column(db.Boolean, default=False, nullable=False)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    expires_at: datetime = db.Column(db.DateTime, nullable=False)  # type: ignore


class HSClassification(Base):
    """HS分類結果モデル"""

    __tablename__ = "hs_classifications"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    product_id: Optional[str] = db.Column(db.String(128), index=True, nullable=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore

    product_name: str = db.Column(db.Text, nullable=False)  # type: ignore
    category: Optional[str] = db.Column(db.String(64), nullable=True, index=True)  # type: ignore
    origin_country: Optional[str] = db.Column(db.String(2), nullable=True)  # type: ignore
    ingredients: Optional[List[Dict[str, Any]]] = db.Column(db.JSON, nullable=True)  # type: ignore
    process: Optional[List[str]] = db.Column(db.JSON, nullable=True)  # type: ignore

    hs_candidates: List[Dict[str, Any]] = db.Column(db.JSON, nullable=False)  # type: ignore
    final_hs_code: str = db.Column(db.String(16), nullable=False, index=True)  # type: ignore
    required_uom: str = db.Column(db.String(8), nullable=False)  # type: ignore
    review_required: bool = db.Column(db.Boolean, default=False, nullable=False, index=True)  # type: ignore

    duty_rate: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    duty_rate_override: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    risk_flags: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    quota_applicability: Optional[str] = db.Column(db.String(64), nullable=True)  # type: ignore
    explanations: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    status: str = db.Column(db.String(16), nullable=True, default="classified")  # type: ignore
    final_source: Optional[str] = db.Column(db.String(32), nullable=True, default="system")  # type: ignore
    reviewed_by: Optional[str] = db.Column(db.String(128), nullable=True)  # type: ignore
    reviewed_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)  # type: ignore
    review_comment: Optional[str] = db.Column(db.Text, nullable=True)  # type: ignore

    classification_method: str = db.Column(db.String(32), default="rule_based")  # type: ignore
    processing_time_ms: Optional[int] = db.Column(db.Integer, nullable=True)  # type: ignore
    cache_hit: bool = db.Column(db.Boolean, default=False)  # type: ignore
    rules_version: Optional[str] = db.Column(db.String(16), nullable=True)  # type: ignore

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # type: ignore

    def __repr__(self) -> str:
        return f"<HSClassification {self.id} hs={self.final_hs_code} trace={self.trace_id}>"
