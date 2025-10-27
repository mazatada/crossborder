import os
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, BigInteger, LargeBinary
)
from sqlalchemy.dialects.postgresql import JSONB  # Postgres 以外でもimport自体はOK
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship

# --- Engine & Session ---
DB_URL = os.getenv("DB_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///app.db"
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))
Base = declarative_base()

# --- Flask-SQLAlchemy 互換シム ---
class _DB:
    # Flask-SQLAlchemy のよく使うエイリアスを用意
    Model = Base
    Column = Column
    Integer = Integer
    BigInteger = BigInteger
    String = String
    Text = Text
    DateTime = DateTime
    Boolean = Boolean
    Float = Float
    ForeignKey = ForeignKey
    JSON = JSON
    JSONB = JSONB
    LargeBinary = LargeBinary
    relationship = staticmethod(relationship)

    # 便利エイリアス
    engine = engine
    session = SessionLocal

    def init_app(self, app):
        # Flask アプリと統合する場合のダミー（互換目的）
        return None

    @property
    def metadata(self):
        # db.metadata で SQLAlchemy Metadata を返す（互換用）
        return self.Model.metadata

db = _DB()

# 既存コード用：コンテキストマネージャ
@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    """テーブル作成（必要なら呼ばれる）"""
    Base.metadata.create_all(bind=engine)
