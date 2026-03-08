from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import validates
from ..db import db, Base


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

    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore
    updated_at: datetime = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )  # type: ignore

    def __repr__(self) -> str:
        return f"<HSClassification {self.id} hs={self.final_hs_code} trace={self.trace_id}>"

    # ステータス遷移の順序定義（クラスレベルで定義して効率化）
    _STATUS_ORDER = {
        "pending": 0,
        "in_progress": 1,
        "classified": 1,
        "locked": 2,
        "reviewed": 3,
        "superseded": 4,
    }

    @validates("status")
    def validate_status(self, key, value):
        new_rank = self._STATUS_ORDER.get(value, -1)
        if new_rank == -1:
            raise ValueError(f"Invalid state: '{value}' is an unrecognized status")

        # 既存ステータスがある場合のみ遷移チェック
        if self.status:
            old_rank = self._STATUS_ORDER.get(self.status, -1)
            if old_rank > new_rank and old_rank != -1:
                raise ValueError(
                    f"Invalid state transition from {self.status} to {value}"
                )
        return value
