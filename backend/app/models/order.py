from datetime import datetime
from typing import Optional
from sqlalchemy import UniqueConstraint, func
from ..db import db, Base


class OrderStatus(Base):
    __tablename__ = "order_statuses"
    __table_args__ = (UniqueConstraint("order_id", "status", name="uq_order_status"),)
    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)  # type: ignore
    order_id: str = db.Column(db.String(128), nullable=False, index=True)  # type: ignore
    status: str = db.Column(db.String(32), nullable=False)  # type: ignore
    ts: datetime = db.Column(db.DateTime, nullable=False)  # type: ignore
    customer_region: Optional[str] = db.Column(db.String(64), nullable=True)  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
