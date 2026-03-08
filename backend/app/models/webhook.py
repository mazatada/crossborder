from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func
from ..db import db, Base


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    url: str = db.Column(db.String(512), nullable=False)  # type: ignore
    secret: str = db.Column(db.String(128), nullable=False)  # type: ignore
    events: List[str] = db.Column(db.JSON, nullable=False)  # type: ignore
    active: bool = db.Column(db.Boolean, default=True, nullable=False)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )  # type: ignore


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
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    expires_at: datetime = db.Column(db.DateTime, nullable=False, index=True)  # type: ignore
