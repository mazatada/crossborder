# backend/app/db.py
import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db():
    # Alembic 実行中・本番では create_all をしない（migrations で管理）
    if os.getenv("ALEMBIC_RUNNING") or os.getenv("DISABLE_CREATE_ALL"):
        return
    # 開発の超初期だけ許すなら下を生かす。原則はコメントアウト推奨
    # from .models import Job, DocumentPackage, MediaBlob, PNSubmission, Audit
    # db.create_all()
