"""IdempotencyRecord model for API-level idempotency (Phase 4a)."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import func, UniqueConstraint
from ..db import db, Base


class IdempotencyRecord(Base):
    """Tracks idempotency keys to prevent duplicate processing.

    Each record represents a unique (scope, idempotency_key) pair.
    scope is typically the API endpoint path (e.g. '/v1/docs/clearance-pack').
    """

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("scope", "idempotency_key", name="uq_idempotency_scope_key"),
    )

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    scope: str = db.Column(db.String(128), nullable=False, index=True)  # type: ignore
    idempotency_key: str = db.Column(db.String(128), nullable=False)  # type: ignore

    status: str = db.Column(
        db.String(16), nullable=False, default="IN_PROGRESS"
    )  # type: ignore
    # IN_PROGRESS | COMPLETED | FAILED

    response_code: Optional[int] = db.Column(db.Integer, nullable=True)  # type: ignore
    response_body: Optional[Dict[str, Any]] = db.Column(db.JSON, nullable=True)  # type: ignore
    resource_type: Optional[str] = db.Column(db.String(64), nullable=True)  # type: ignore
    resource_id: Optional[str] = db.Column(db.String(128), nullable=True)  # type: ignore

    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )  # type: ignore
