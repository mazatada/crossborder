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
    # 環境変数をインメモリ SQLite に固定。これで app.db が初期化時にこれを参照する。
    os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    os.environ["API_KEYS"] = "test-api-key"
    os.environ["TESTING"] = "true"

    from app.factory import create_app
    from app.db import engine as _engine
    
    # 既存の engine が Postgres を向いている可能性があれば dispose (念の為)
    _engine.dispose()
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key"
    })
    return app

@pytest.fixture(scope="function")
def app(_app):
    """Per-test application with clean DB."""
    from app.db import db
    
    with _app.app_context():
        # 清掃
        db.session.remove()
        db.metadata.drop_all(bind=db.engine)
        # 作成
        db.metadata.create_all(bind=db.engine)
        # ジョブ関連のテーブルが確実に作成されているか確認 (debug用)
        # print(f"Tables: {db.metadata.tables.keys()}")
        yield _app
        # 終了処理
        db.session.remove()
        db.metadata.drop_all(bind=db.engine)

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
