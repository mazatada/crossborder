from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from ..db import db, Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    trace_id: str = db.Column(db.String(64), index=True, nullable=False)  # type: ignore
    event: str = db.Column(db.String(64), nullable=False)  # type: ignore
    payload: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    ts: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False, index=True)  # type: ignore
