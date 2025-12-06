# app/audit.py
from __future__ import annotations
import json
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import db

CHECK_COL_SQL = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema='public' AND table_name='audit_events'
ORDER BY ordinal_position;
"""

CREATE_NEW_SQL = """
CREATE TABLE IF NOT EXISTS public.audit_events (
  id           BIGSERIAL PRIMARY KEY,
  at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id     TEXT,
  event        TEXT NOT NULL,
  target_type  TEXT,
  target_id    BIGINT,
  details_json JSONB
);
CREATE INDEX IF NOT EXISTS idx_audit_events_at        ON public.audit_events (at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_trace_id  ON public.audit_events (trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event     ON public.audit_events (event);
"""


def _detect_schema(conn) -> str:
    cols = [r[0] for r in conn.execute(text(CHECK_COL_SQL)).fetchall()]
    if not cols:
        conn.execute(text(CREATE_NEW_SQL))
        return "new"
    if "ts" in cols and "payload" in cols and "event" in cols:
        return "old"
    if "at" in cols and "details_json" in cols and "event" in cols:
        return "new"
    return "new"


def record_event(
    *,
    event: str,
    trace_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    **details: Any,
) -> None:
    """
    監査イベントを書き込む。メイン処理とは独立TXで保存し、失敗しても絶対に本処理を止めない。
    旧スキーマ(audit_events: id, ts, event, trace_id, payload) / 新スキーマの両方に対応。
    """
    try:
        engine = db.engine
        with engine.begin() as conn:  # ← メインの db.session とは分離
            schema = _detect_schema(conn)
            if schema == "old":
                payload = {
                    "target_type": target_type,
                    "target_id": target_id,
                    **(details or {}),
                }
                conn.execute(
                    text(
                        """
                        INSERT INTO public.audit_events (ts, trace_id, event, payload)
                        VALUES (now(), :trace_id, :event, CAST(:payload AS JSONB))
                    """
                    ),
                    {
                        "trace_id": trace_id,
                        "event": event,
                        "payload": json.dumps(payload, ensure_ascii=False),
                    },
                )
            else:
                details_json_str = json.dumps(details, ensure_ascii=False) if details else None
                conn.execute(
                    text(
                        """
                        INSERT INTO public.audit_events (at, trace_id, event, target_type, target_id, details_json)
                        VALUES (now(), :trace_id, :event, :target_type, :target_id, CAST(:details_json AS JSONB))
                    """
                    ),
                    {
                        "trace_id": trace_id,
                        "event": event,
                        "target_type": target_type,
                        "target_id": target_id,
                        "details_json": details_json_str,
                    },
                )
    except SQLAlchemyError:
        # 監査は副作用。完全に黙殺して本処理を継続
        pass


# エイリアス
log_event = record_event
