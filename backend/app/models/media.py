from datetime import datetime
from sqlalchemy import func
from ..db import db, Base


class MediaBlob(Base):
    __tablename__ = "media_blobs"
    media_id: str = db.Column(db.String(128), primary_key=True)  # type: ignore
    sha256: str = db.Column(db.String(64), nullable=False)  # type: ignore
    size: int = db.Column(db.BigInteger, nullable=False)  # type: ignore
    mime: str = db.Column(db.String(64), nullable=False, default="application/octet-stream")  # type: ignore
    created_at: datetime = db.Column(db.DateTime, server_default=func.now(), nullable=False)  # type: ignore


Artifact = MediaBlob
