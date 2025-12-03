# app/factory.py
import os
from flask import Flask
from flask_cors import CORS
from app.api import v1_misc, v1_jobs, v1_translate, v1_classify, v1_docs, v1_pn, v1_audit, v1_webhooks, v1_inbound

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DB_URL")
    JSON_AS_ASCII = False

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    app.register_blueprint(v1_misc.bp)
    app.register_blueprint(v1_jobs.bp)
    app.register_blueprint(v1_translate.bp)
    app.register_blueprint(v1_classify.bp)
    app.register_blueprint(v1_docs.bp)
    app.register_blueprint(v1_pn.bp)
    app.register_blueprint(v1_audit.bp)
    app.register_blueprint(v1_webhooks.bp)
    app.register_blueprint(v1_inbound.bp)
    return app