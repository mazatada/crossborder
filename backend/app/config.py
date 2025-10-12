import os
class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DB_URL","sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY","dev")
