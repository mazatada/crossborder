# app/factory.py
import os
import uuid
import json
from flask import Flask, request, g
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
    v1_products,
)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv(
        "DB_URL"
    )
    JSON_AS_ASCII = False


def create_app():
    from app.logging_conf import (
        setup_logging,
        get_trace_id,
        set_trace_id,
        reset_trace_id,
    )

    setup_logging()

    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    @app.before_request
    def start_trace():
        tid = request.headers.get("X-Trace-Id") or request.headers.get("X-Trace-ID")
        if not tid:
            tid = f"req-{uuid.uuid4().hex[:8]}"
        g.trace_id_token = set_trace_id(tid)

    @app.after_request
    def end_trace_and_audit(response):
        tid = get_trace_id()
        if tid:
            response.headers["X-Trace-Id"] = tid
            if response.is_json:
                try:
                    data = response.get_json(silent=True)
                    if isinstance(data, dict) and "trace_id" not in data:
                        data["trace_id"] = tid
                        response.set_data(json.dumps(data))
                except Exception:
                    pass

        # === Phase 1.5: API Middleware Logging & Masking ===
        if request.path.startswith("/v1/") and request.method != "OPTIONS":
            from app.audit import log_event

            req_body = None
            try:
                # view_function 実行後なのでストリーム枯渇は起きず安全に読める
                raw = request.get_data(as_text=True)
                if raw:
                    req_body = json.loads(raw)
                    if isinstance(req_body, dict):
                        for k in list(req_body.keys()):
                            # PII / Secret MASKING
                            if any(
                                sub in k.lower()
                                for sub in ["password", "secret", "key", "token"]
                            ):
                                req_body[k] = "***MASKED***"
            except Exception:
                pass

            try:
                log_event(
                    trace_id=tid,
                    event=f"api.response.{response.status_code}",
                    target_type="http_request",
                    path=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    request_payload=req_body,
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Audit middleware failed: {e}")

        return response

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        from werkzeug.exceptions import HTTPException

        if isinstance(e, HTTPException):
            return e

        import traceback
        import logging
        from flask import jsonify

        tid = get_trace_id()
        logging.getLogger(__name__).error(
            f"Unhandled exception [trace_id={tid}]: {e}\n{traceback.format_exc()}"
        )

        from app.audit import log_event

        try:
            log_event(
                trace_id=tid,
                event="api.response.500",
                target_type="http_request",
                path=request.path,
                method=request.method,
                status_code=500,
                error=str(e),
            )
        except Exception:
            pass

        return jsonify({"error": "Internal Server Error", "trace_id": tid}), 500

    @app.teardown_request
    def cleanup_trace(exception=None):
        token = getattr(g, "trace_id_token", None)
        if token:
            reset_trace_id(token)

    # ── DB テーブル自動作成（Alembic 非適用環境のフォールバック）──
    from app import models  # noqa: F401
    from app.db import init_db

    try:
        init_db()
    except Exception:
        import logging

        logging.getLogger(__name__).warning("init_db failed (non-fatal)", exc_info=True)

    # ── セッションライフサイクル管理 ──
    # scoped_session をリクエスト終了時に確実にクリーンアップ。
    # これがないと、前リクエストで壊れたセッション状態が次リクエストに伝播し
    # 500エラーを引き起こす（例: classifyのcommit失敗 → docsの500）。
    from app.db import db as _db

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        _db.session.remove()

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
    app.register_blueprint(v1_products.bp)
    return app
