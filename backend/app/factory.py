# app/factory.py
import os
import uuid

from flask import Flask, request as flask_request
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
)
from app.api import v1_hs_rules, v1_hs_review, v1_compliance
from app.audit import set_trace_id


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv(
        "DB_URL"
    )
    JSON_AS_ASCII = False


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # --- Trace ID ミドルウェア ---
    @app.before_request
    def _inject_trace_id():
        """
        リクエストヘッダの X-Trace-ID を優先取得し、
        なければ自動生成して contextvars にセットする。
        """
        tid = flask_request.headers.get("X-Trace-ID") or uuid.uuid4().hex[:16]
        set_trace_id(tid)

    # --- Blueprint 登録 ---
    app.register_blueprint(v1_misc.bp)
    app.register_blueprint(v1_jobs.bp)
    app.register_blueprint(v1_translate.bp)
    app.register_blueprint(v1_classify.bp)
    app.register_blueprint(v1_docs.bp)
    app.register_blueprint(v1_pn.bp)
    app.register_blueprint(v1_audit.bp)
    app.register_blueprint(v1_webhooks.bp)
    app.register_blueprint(v1_inbound.bp)
    app.register_blueprint(v1_hs_rules.bp)
    app.register_blueprint(v1_hs_review.bp)
    app.register_blueprint(v1_compliance.bp)
    return app
