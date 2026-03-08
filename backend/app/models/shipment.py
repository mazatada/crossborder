from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import validates
from ..db import db, Base


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

    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
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

    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore


class DocumentExport(Base):
    __tablename__ = "document_exports"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    shipment_id: int = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)  # type: ignore
    type: str = db.Column(db.String(32), nullable=False)  # type: ignore
    format: str = db.Column(db.String(16), nullable=False)  # type: ignore
    s3_key: Optional[str] = db.Column(db.String(512), nullable=True)  # type: ignore
    storage_url: Optional[str] = db.Column(db.String(512), nullable=True)  # type: ignore
    schema_version: str = db.Column(db.String(16), nullable=False, default="1.0")  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
