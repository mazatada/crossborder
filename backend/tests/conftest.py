import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def _app():
    """Session-wide test `Flask` application factory."""
    os.environ["API_KEYS"] = "test-api-key"
    os.environ["TESTING"] = "true"

    from app.factory import create_app

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key"
    })
    return app

@pytest.fixture(scope="function")
def app(_app):
    """Per-test application with clean DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker
    import app.db as app_db

    sqlite_engine = create_engine("sqlite:///:memory:", future=True)
    sqlite_session = scoped_session(
        sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False, future=True)
    )

    # Swap DB engine/session to SQLite for isolated tests, then restore after.
    original_engine = app_db.engine
    original_session = app_db.SessionLocal
    original_db_engine = app_db.db.engine
    original_db_session = app_db.db.session

    app_db.engine = sqlite_engine
    app_db.SessionLocal = sqlite_session
    app_db.db.engine = sqlite_engine
    app_db.db.session = sqlite_session

    with _app.app_context():
        # SQLite needs Integer PK for autoincrement; adjust Job.id just for test schema.
        from app.models import Job
        from sqlalchemy import Integer
        Job.__table__.columns["id"].type = Integer()
        # 清掃
        sqlite_session.remove()
        app_db.Base.metadata.drop_all(bind=sqlite_engine)
        # 作成
        app_db.Base.metadata.create_all(bind=sqlite_engine)
        # ジョブ関連のテーブルが確実に作成されているか確認 (debug用)
        # print(f"Tables: {db.metadata.tables.keys()}")
        yield _app
        # 終了処理
        sqlite_session.remove()
        app_db.Base.metadata.drop_all(bind=sqlite_engine)

    app_db.engine = original_engine
    app_db.SessionLocal = original_session
    app_db.db.engine = original_db_engine
    app_db.db.session = original_db_session

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture(scope="function")
def db_session(app):
    """DB session fixture (function scope)"""
    from app.db import db
    return db.session


@pytest.fixture
def api_key_header():
    """APIキーヘッダー"""
    return {"Authorization": "Bearer test-api-key"}
