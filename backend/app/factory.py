# app/factory.py
import os
from flask import Flask
from flask_cors import CORS
from app.api import (
    v1_misc,
    v1_jobs,
    v1_translate,
    v1_classify,
    v1_docs,
    v1_pn,
    v1_audit,
    v1_webhooks,
    v1_inbound,
    v1_tariffs,
    v1_hs_review,
    v1_hs_rules,
    v1_compliance,
)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv(
        "DB_URL"
    )
    JSON_AS_ASCII = False


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # ── DB テーブル自動作成（Alembic 非適用環境のフォールバック）──
    # models.py をインポートすることで Base.metadata にテーブル定義を登録
    import app.models  # noqa: F401
    from app.db import init_db
    try:
        init_db()
    except Exception:
        # CI/テスト等でDB未到達の場合は致命的ではないため続行
        import logging
        logging.getLogger(__name__).warning("init_db failed (non-fatal)", exc_info=True)

    app.register_blueprint(v1_misc.bp)
    app.register_blueprint(v1_jobs.bp)
    app.register_blueprint(v1_translate.bp)
    app.register_blueprint(v1_classify.bp)
    app.register_blueprint(v1_docs.bp)
    app.register_blueprint(v1_pn.bp)
    app.register_blueprint(v1_audit.bp)
    app.register_blueprint(v1_webhooks.bp)
    app.register_blueprint(v1_inbound.bp)
    app.register_blueprint(v1_tariffs.bp)
    app.register_blueprint(v1_hs_review.bp)
    app.register_blueprint(v1_hs_rules.bp)
    app.register_blueprint(v1_compliance.bp)
    return app
