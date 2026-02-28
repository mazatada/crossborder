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

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.audit_events (
  id           BIGSERIAL PRIMARY KEY,
  at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_id     TEXT,
  event        TEXT NOT NULL,
  target_type  TEXT,
  target_id    BIGINT,
  details_json JSONB
);
"""

CREATE_INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_audit_events_at        ON public.audit_events (at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_trace_id  ON public.audit_events (trace_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_event     ON public.audit_events (event);",
]


def _is_sqlite(conn) -> bool:
    """接続先が SQLite かどうか判定する"""
    return "sqlite" in str(conn.engine.url)


def _detect_schema(conn) -> str:
    if _is_sqlite(conn):
        # SQLite: テーブルの存在チェック
        rows = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
            )
        ).fetchall()
        if not rows:
            # SQLite用の簡易テーブル作成
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_events (
                  id           INTEGER PRIMARY KEY AUTOINCREMENT,
                  at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  trace_id     TEXT,
                  event        TEXT NOT NULL,
                  target_type  TEXT,
                  target_id    INTEGER,
                  details_json TEXT
                )
            """))
            return "new"
        cols = [
            r[1]
            for r in conn.execute(text("PRAGMA table_info(audit_events)")).fetchall()
        ]
        if "ts" in cols and "payload" in cols:
            return "old"
        return "new"
    else:
        # PostgreSQL
        cols = [r[0] for r in conn.execute(text(CHECK_COL_SQL)).fetchall()]
        if not cols:
            # 複文を個別に実行（psycopg3互換）
            conn.execute(text(CREATE_TABLE_SQL))
            for idx_sql in CREATE_INDEX_SQLS:
                conn.execute(text(idx_sql))
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
    target_id: Optional[str] = None,
    target_key: Optional[str] = None,
    **details: Any,
) -> None:
    """
    監査イベントを書き込む。メイン処理とは独立TXで保存し、失敗しても絶対に本処理を止めない。
    """
    import uuid
    if not trace_id:
        trace_id = f"audit-{uuid.uuid4().hex[:8]}"

    # Backwards compatibility: use target_key if provided, else target_id
    effective_target = target_key if target_key is not None else target_id

    try:
        engine = db.engine
        with engine.begin() as conn:  # ← メインの db.session とは分離
            schema = _detect_schema(conn)
            sqlite = _is_sqlite(conn)
            tbl = "audit_events" if sqlite else "public.audit_events"

            if schema == "old":
                payload = {
                    "target_type": target_type,
                    "target_key": effective_target,
                    **(details or {}),
                }
                payload_str = json.dumps(payload, ensure_ascii=False)
                if sqlite:
                    sql = f"INSERT INTO {tbl} (ts, trace_id, event, payload) VALUES (CURRENT_TIMESTAMP, :trace_id, :event, :payload)"
                else:
                    sql = f"INSERT INTO {tbl} (ts, trace_id, event, payload) VALUES (now(), :trace_id, :event, CAST(:payload AS JSONB))"
                conn.execute(
                    text(sql),
                    {
                        "trace_id": trace_id,
                        "event": event,
                        "payload": payload_str,
                    },
                )
            else:
                details_json_str = (
                    json.dumps(details, ensure_ascii=False) if details else None
                )
                
                # target_id は BIGINT/INTEGER なので数値変換を試みる
                t_id_int = None
                try:
                    if effective_target is not None:
                        t_id_int = int(effective_target)
                except (ValueError, TypeError):
                    # 文字列IDの場合は details_json に退避
                    if details_json_str is None:
                        details_json_str = json.dumps({"target_key": effective_target}, ensure_ascii=False)
                    else:
                        d = details.copy()
                        d["target_key"] = effective_target
                        details_json_str = json.dumps(d, ensure_ascii=False)

                if sqlite:
                    sql = f"INSERT INTO {tbl} (at, trace_id, event, target_type, target_id, details_json) VALUES (CURRENT_TIMESTAMP, :trace_id, :event, :target_type, :target_id, :details_json)"
                else:
                    sql = f"INSERT INTO {tbl} (at, trace_id, event, target_type, target_id, details_json) VALUES (now(), :trace_id, :event, :target_type, :target_id, CAST(:details_json AS JSONB))"
                conn.execute(
                    text(sql),
                    {
                        "trace_id": trace_id,
                        "event": event,
                        "target_type": target_type,
                        "target_id": t_id_int,
                        "details_json": details_json_str,
                    },
                )
    except SQLAlchemyError:
        # 監査は副作用。完全に黙殺して本処理を継続
        pass


# エイリアス
log_event = record_event
