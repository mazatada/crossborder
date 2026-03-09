from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from ..db import db, Base


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

    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )  # type: ignore
