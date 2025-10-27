# app/factory.py
import os
from flask import Flask
from flask_cors import CORS

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DB_URL")
    JSON_AS_ASCII = False

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    from app.api.v1_misc import bp as bp_misc
    app.register_blueprint(bp_misc, url_prefix="/v1")

    from app.api.v1_jobs import bp as jobs_bp
    app.register_blueprint(jobs_bp, url_prefix="/v1")

    return app
