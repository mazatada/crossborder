from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from ..db import db, Base


class PNSubmission(Base):
    __tablename__ = "pn_submissions"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    product: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    logistics: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    importer: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    consignee: Dict[str, Any] = db.Column(db.JSON, nullable=False)  # type: ignore
    label_media_id: Optional[str] = db.Column(db.String(128), db.ForeignKey("media_blobs.media_id"), nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore


class DocumentPackage(Base):
    __tablename__ = "document_packages"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    hs_code: str = db.Column(db.String(16), nullable=False)  # type: ignore
    required_uom: str = db.Column(db.String(8), nullable=False)  # type: ignore
    invoice_uom: str = db.Column(db.String(8), nullable=False)  # type: ignore
    invoice_payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
