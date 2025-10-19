# backend/app/factory.py （該当部分のみ）
import os
from flask import Flask
from flask_cors import CORS
from .config import Config
from .db import db, init_db
from .auth import install_api_key_protection   # ← すでに導入済み前提

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())
    CORS(app, resources={r"/v1/*": {"origins": "*"}})
    db.init_app(app)

    # Alembic 実行時のみ create_all を抑止
    if not os.getenv("ALEMBIC_RUNNING"):
        with app.app_context():
            init_db()

    # ★ Blueprint の import/登録は常に実行する
    from .api.v1_classify import bp as bp_classify
    from .api.v1_misc import bp as bp_misc
    from .api.v1_pn import bp as bp_pn
    from .api.v1_docs import bp as bp_docs
    from .api.v1_jobs import bp as bp_jobs
    from .api.v1_export import bp as bp_export
    from .api.v1_translate_stub import bp as bp_translate
    from .api.v1_audit import bp as bp_audit

    app.register_blueprint(bp_classify, url_prefix="/v1")
    app.register_blueprint(bp_misc,     url_prefix="/v1")  # ← これが health/version
    app.register_blueprint(bp_pn,       url_prefix="/v1")
    app.register_blueprint(bp_docs,     url_prefix="/v1")
    app.register_blueprint(bp_jobs,     url_prefix="/v1")
    app.register_blueprint(bp_export,   url_prefix="/v1")
    app.register_blueprint(bp_translate,url_prefix="/v1")
    app.register_blueprint(bp_audit,    url_prefix="/v1")

    # APIキー保護（health/version/static は免除）
    install_api_key_protection(app, exempt_prefixes=["/v1/health", "/v1/version", "/static"])

    return app
