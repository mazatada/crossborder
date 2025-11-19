import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.audit import record_event


@pytest.mark.ultracite
def test_record_event_swallow(monkeypatch):
    class DummyCtx:
        class DummyConn:
            def execute(self, *args, **kwargs):
                raise SQLAlchemyError("audit fail")

        def __enter__(self):
            return self.DummyConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.audit._detect_schema", lambda conn: "new")
    monkeypatch.setattr("app.audit.db.engine.begin", lambda: DummyCtx())
    # Should not raise even though the inner execute raises SQLAlchemyError
    record_event(event="TEST_EVENT", trace_id="monitor-123")
