from datetime import datetime
from typing import Optional, List, Dict, Any
from .db import db


class Job(db.Model):
    __tablename__ = "jobs"
    id: int = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    type: str = db.Column(db.String(16), nullable=False)  # "pack" | "pn" | etc
    status: str = db.Column(db.String(16), nullable=False, index=True)
    trace_id: Optional[str] = db.Column(db.String(64), index=True)
    error: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)

    # 追加済みのカラム（migrations で作ったやつ）
    attempts: int = db.Column(db.Integer, nullable=False, default=0)
    next_run_at: Optional[datetime] = db.Column(db.DateTime, nullable=True)
    payload_json: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)
    result_json: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class MediaBlob(db.Model):
    __tablename__ = "media_blobs"
    media_id: str = db.Column(db.String(128), primary_key=True)
    sha256: str = db.Column(db.String(64), nullable=False)
    size: int = db.Column(db.Integer, nullable=False)
    mime: str = db.Column(db.String(64), nullable=False, default="application/octet-stream")
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


Artifact = MediaBlob


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)
    event: str = db.Column(db.String(64), nullable=False)
    payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)
    ts: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PNSubmission(db.Model):
    __tablename__ = "pn_submissions"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)
    product: Dict[str, Any] = db.Column(db.JSON, nullable=False)
    logistics: Dict[str, Any] = db.Column(db.JSON, nullable=False)
    importer: Dict[str, Any] = db.Column(db.JSON, nullable=False)
    consignee: Dict[str, Any] = db.Column(db.JSON, nullable=False)
    label_media_id: Optional[str] = db.Column(db.String(128), nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class DocumentPackage(db.Model):
    __tablename__ = "document_packages"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)
    hs_code: str = db.Column(db.String(16), nullable=False)
    required_uom: str = db.Column(db.String(8), nullable=False)
    invoice_uom: str = db.Column(db.String(8), nullable=False)
    invoice_payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class WebhookEndpoint(db.Model):
    __tablename__ = "webhook_endpoints"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url: str = db.Column(db.String(512), nullable=False)
    secret: str = db.Column(db.String(128), nullable=False)  # HMAC secret
    events: List[str] = db.Column(db.JSON, nullable=False)  # List of event types to subscribe
    active: bool = db.Column(db.Boolean, default=True, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class OrderStatus(db.Model):
    __tablename__ = "order_statuses"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id: str = db.Column(db.String(128), nullable=False, index=True)
    status: str = db.Column(db.String(32), nullable=False)  # PAID, CANCELED
    ts: datetime = db.Column(db.DateTime, nullable=False)  # Timestamp from external system
    customer_region: Optional[str] = db.Column(db.String(64), nullable=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class WebhookDLQ(db.Model):
    __tablename__ = "webhook_dlq"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    webhook_id: int = db.Column(
        db.Integer, db.ForeignKey("webhook_endpoints.id"), nullable=False
    )
    event_type: str = db.Column(db.String(64), nullable=False)
    payload: Dict[str, Any] = db.Column(db.JSON, nullable=False)
    trace_id: Optional[str] = db.Column(db.String(64), index=True, nullable=True)
    attempts: int = db.Column(db.Integer, nullable=False, default=0)
    last_error: Optional[str] = db.Column(db.Text, nullable=True)
    last_status_code: Optional[int] = db.Column(db.Integer, nullable=True)
    replayed: bool = db.Column(db.Boolean, default=False, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at: datetime = db.Column(db.DateTime, nullable=False)  # 72 hours from creation


class HSClassification(db.Model):
    """HS分類結果モデル"""

    __tablename__ = "hs_classifications"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id: Optional[str] = db.Column(db.String(128), index=True, nullable=True)
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)

    # 入力データ (product object)
    product_name: str = db.Column(db.Text, nullable=False)
    category: Optional[str] = db.Column(db.String(64), nullable=True, index=True)
    origin_country: Optional[str] = db.Column(db.String(2), nullable=True)
    ingredients: Optional[List[Dict[str, Any]]] = db.Column(db.JSON, nullable=True)  # [{"id": "ing_xxx", "pct": 30.0}]
    process: Optional[List[str]] = db.Column(db.JSON, nullable=True)  # ["baking", "packaging"]

    # 分類結果 (hs_candidates)
    hs_candidates: List[Dict[str, Any]] = db.Column(db.JSON, nullable=False)  # 全候補 (OpenAPI準拠)
    final_hs_code: str = db.Column(db.String(16), nullable=False, index=True)
    required_uom: str = db.Column(db.String(8), nullable=False)
    review_required: bool = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # 拡張フィールド
    duty_rate: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)
    risk_flags: Optional[List[str]] = db.Column(db.JSON, nullable=True)
    quota_applicability: Optional[str] = db.Column(db.String(64), nullable=True)
    explanations: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)

    # メタデータ
    classification_method: str = db.Column(db.String(32), default="rule_based")
    processing_time_ms: Optional[int] = db.Column(db.Integer, nullable=True)
    cache_hit: bool = db.Column(db.Boolean, default=False)
    rules_version: Optional[str] = db.Column(db.String(16), nullable=True)

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<HSClassification {self.id} hs={self.final_hs_code} trace={self.trace_id}>"
