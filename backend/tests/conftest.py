import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def app():
    from app.factory import create_app

    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from app.db import init_db

    init_db()
    yield


@pytest.fixture
def api_key_header():
    """APIキーヘッダー"""
    # テスト用のAPIキーを設定
    os.environ.setdefault("API_KEYS", "test-api-key")
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def db_session():
    """DBセッション"""
    from app.db import db

    return db.session
