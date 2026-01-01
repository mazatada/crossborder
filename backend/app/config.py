# backend/app/config.py
import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI not set")  # フォールバック禁止
    SQLALCHEMY_TRACK_MODIFICATIONS = False
