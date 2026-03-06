from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import validates
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
    ts: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)  # type: ignore


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
    expires_at: datetime = db.Column(db.DateTime, nullable=False, index=True)  # type: ignore


class HSClassification(Base):
    """HS分類結果モデル"""

    __tablename__ = "hs_classifications"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    product_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True)  # type: ignore
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
    locked_by: Optional[str] = db.Column(db.String(128), nullable=True)  # type: ignore
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

    @validates("status")
    def validate_status(self, key, value):
        if self.status:
            order = {
                "pending": 0,
                "in_progress": 1,
                "classified": 1,
                "locked": 2,
                "reviewed": 3,
                "superseded": 4,
            }
            old_rank = order.get(self.status, -1)
            new_rank = order.get(value, -1)
            if new_rank == -1:
                raise ValueError(f"Invalid state: '{value}' is an unrecognized status")
            if old_rank > new_rank and old_rank != -1:
                raise ValueError(
                    f"Invalid state transition from {self.status} to {value}"
                )
        return value


class Product(Base):
    __tablename__ = "products"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    external_ref: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    title: str = db.Column(db.String(255), nullable=False)  # type: ignore
    description_en: Optional[str] = db.Column(db.Text, nullable=True)  # type: ignore
    origin_country: str = db.Column(db.String(2), nullable=False, default="XX")  # type: ignore
    is_food: bool = db.Column(db.Boolean, default=False, nullable=False)  # type: ignore
    processing_state: Optional[str] = db.Column(db.String(32), nullable=True)  # type: ignore
    physical_form: Optional[str] = db.Column(db.String(32), nullable=True)  # type: ignore
    unit_weight_g: Optional[int] = db.Column(db.Integer, nullable=True)  # type: ignore
    dimensions_mm: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    shelf_life_days: Optional[int] = db.Column(db.Integer, nullable=True)  # type: ignore
    packaging: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    animal_derived_flags: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    # Final cached values from classification
    hs_base6: Optional[str] = db.Column(db.String(16), nullable=True)  # type: ignore
    active_classification_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("hs_classifications.id", name="fk_product_active_classification", use_alter=True, ondelete="SET NULL"), nullable=True)  # type: ignore
    country_specific_codes: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    active_classification = db.relationship(
        "HSClassification",
        foreign_keys="[Product.active_classification_id]",
        post_update=True,
    )

    status: str = db.Column(db.String(32), nullable=False, default="draft")  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # type: ignore


class Shipment(Base):
    __tablename__ = "shipments"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    order_ref: Optional[str] = db.Column(db.String(128), index=True, nullable=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    destination_country: str = db.Column(db.String(2), nullable=False)  # type: ignore
    shipping_mode: str = db.Column(db.String(32), nullable=False)  # type: ignore
    incoterm: str = db.Column(db.String(8), nullable=False, default="DDP")  # type: ignore
    currency: str = db.Column(db.String(3), nullable=False, default="USD")  # type: ignore
    total_value: float = db.Column(db.Float, nullable=False, default=0.0)  # type: ignore
    total_weight_g: int = db.Column(db.Integer, nullable=False, default=0)  # type: ignore

    status: str = db.Column(db.String(32), nullable=False, default="draft")  # type: ignore
    validation_errors: Optional[List[Dict[str, Any]]] = db.Column(db.JSON, nullable=True)  # type: ignore

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # type: ignore

    lines = db.relationship("ShipmentLine", backref="shipment", lazy="dynamic")
    exports = db.relationship("DocumentExport", backref="shipment", lazy="dynamic")

    VALID_STATUSES = [
        "draft",
        "validated",
        "generating",
        "completed",
        "failed",
        "canceled",
    ]

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in self.VALID_STATUSES:
            raise ValueError(f"Invalid Shipment status: '{value}'")
        if self.status:
            allowed: dict[str, list[str]] = {
                "draft": ["validated", "canceled"],
                "validated": ["generating", "draft", "canceled"],
                "generating": ["completed", "failed"],
                "completed": [],
                "failed": ["draft"],
                "canceled": [],
            }
            if value not in allowed.get(self.status, []):
                raise ValueError(
                    f"Invalid Shipment state transition: {self.status} -> {value}"
                )
        return value


class ShipmentLine(Base):
    __tablename__ = "shipment_lines"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    shipment_id: int = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)  # type: ignore
    product_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)  # type: ignore

    qty: int = db.Column(db.Integer, nullable=False, default=1)  # type: ignore
    unit_price: float = db.Column(db.Float, nullable=False, default=0.0)  # type: ignore
    currency: str = db.Column(db.String(3), nullable=False, default="USD")  # type: ignore
    line_value: float = db.Column(db.Float, nullable=False, default=0.0)  # type: ignore
    line_weight_g: int = db.Column(db.Integer, nullable=False, default=0)  # type: ignore

    # Snapshot fields (frozen copy at time of shipment creation to prevent audit desync)
    hs_base6: Optional[str] = db.Column(db.String(16), nullable=True)  # type: ignore
    country_specific_code: Optional[str] = db.Column(db.String(32), nullable=True)  # type: ignore
    origin_country: str = db.Column(db.String(2), nullable=False)  # type: ignore
    description_en: Optional[str] = db.Column(db.Text, nullable=True)  # type: ignore
    product_snapshot: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore


class DocumentExport(Base):
    __tablename__ = "document_exports"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    shipment_id: int = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)  # type: ignore
    type: str = db.Column(db.String(32), nullable=False)  # type: ignore
    format: str = db.Column(db.String(16), nullable=False)  # type: ignore
    s3_key: Optional[str] = db.Column(db.String(512), nullable=True)  # type: ignore
    storage_url: Optional[str] = db.Column(db.String(512), nullable=True)  # type: ignore
    schema_version: str = db.Column(db.String(16), nullable=False, default="1.0")  # type: ignore
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # type: ignore
