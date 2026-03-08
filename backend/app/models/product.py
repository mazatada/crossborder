from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from ..db import db, Base


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
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )  # type: ignore
