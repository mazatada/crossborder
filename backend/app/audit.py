# app/audit.py
"""
監査ログ基盤モジュール (Task 2 改修版)

- PIIマスキング: record_event() で保存する details から PII を自動除去
- Trace ID 伝播: contextvars ベースで Web / CLI ワーカー両対応
- 旧スキーマ (ts/payload) / 新スキーマ (at/details_json) 自動検出
"""
from __future__ import annotations

import json
import uuid
import contextvars
from copy import deepcopy
from typing import Any, Dict, Optional, Set

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import db

# ---------------------------------------------------------------------------
# Trace ID コンテキスト伝播 (contextvars ベース)
# ---------------------------------------------------------------------------
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def set_trace_id(trace_id: str) -> None:
    """現在のコンテキストに trace_id をセットする (API / ワーカー双方で利用)"""
    _trace_id_ctx.set(trace_id)


def get_current_trace_id() -> Optional[str]:
    """
    現在のコンテキストから trace_id を取得する。
    Web リクエスト時: before_request ミドルウェアで set_trace_id() 済み
    ワーカー時: ジョブ開始時に set_trace_id(job.trace_id) 済み
    どちらでもない場合: None を返す（record_event 側でフォールバック生成）
    """
    return _trace_id_ctx.get()


# ---------------------------------------------------------------------------
# PII マスキング
# ---------------------------------------------------------------------------
_PII_KEYS: Set[str] = {
    "customer_name",
    "customer_email",
    "email",
    "phone",
    "address",
    "address_line1",
    "address_line2",
    "city",
    "postal_code",
    "zip_code",
    "full_name",
    "first_name",
    "last_name",
    "consignee_name",
    "consignee_address",
    "importer_name",
    "importer_address",
}

_MASK = "***"


def mask_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書内の PII キーを '***' に置換する（再帰的）。
    元の辞書は変更しない（deepcopy）。
    """
    masked = deepcopy(data)
    _mask_recursive(masked)
    return masked


def _mask_recursive(obj: Any) -> None:
    """辞書・リストを再帰的に走査して PII キーをマスクする"""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key.lower() in _PII_KEYS:
                obj[key] = _MASK
            else:
                _mask_recursive(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _mask_recursive(item)


# ---------------------------------------------------------------------------
# DB スキーマ検出
# ---------------------------------------------------------------------------
# --- PostgreSQL 用 SQL ---
_PG_CHECK_COL_SQL = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema='public' AND table_name='audit_events'
ORDER BY ordinal_position;
"""

_PG_CREATE_SQL = """
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

# --- SQLite 用 SQL ---
_SQLITE_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS audit_events (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  trace_id     TEXT,
  event        TEXT NOT NULL,
  target_type  TEXT,
  target_id    INTEGER,
  details_json TEXT
);
"""


def _is_sqlite(conn) -> bool:
    """接続先が SQLite かどうか判定する"""
    return "sqlite" in str(conn.engine.url)


def _detect_schema(conn) -> str:
    if _is_sqlite(conn):
        # SQLite: テーブルの存在チェック
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'")
        ).fetchall()
        if not rows:
            conn.execute(text(_SQLITE_CREATE_SQL))
            return "new"
        # カラム情報を取得
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(audit_events)")).fetchall()]
        if "ts" in cols and "payload" in cols:
            return "old"
        return "new"
    else:
        # PostgreSQL
        cols = [r[0] for r in conn.execute(text(_PG_CHECK_COL_SQL)).fetchall()]
        if not cols:
            conn.execute(text(_PG_CREATE_SQL))
            return "new"
        if "ts" in cols and "payload" in cols and "event" in cols:
            return "old"
        if "at" in cols and "details_json" in cols and "event" in cols:
            return "new"
        return "new"


# ---------------------------------------------------------------------------
# record_event (メイン)
# ---------------------------------------------------------------------------
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
    監査イベントを書き込む。
    - メイン処理とは独立TXで保存し、失敗しても絶対に本処理を止めない。
    - trace_id 未指定時は contextvars → フォールバック自動生成の順で補完。
    - details に含まれる PII は自動的にマスキングされる。
    """
    # --- trace_id 解決 ---
    if not trace_id:
        trace_id = get_current_trace_id()
    if not trace_id:
        trace_id = f"audit-{uuid.uuid4().hex[:8]}"

    # --- target 解決 ---
    effective_target = target_key if target_key is not None else target_id

    # --- PII マスキング ---
    masked_details = mask_pii(dict(details)) if details else {}

    try:
        engine = db.engine
        with engine.begin() as conn:
            schema = _detect_schema(conn)
            sqlite = _is_sqlite(conn)

            # テーブル名接頭辞 (SQLite には public スキーマがない)
            tbl = "audit_events" if sqlite else "public.audit_events"

            if schema == "old":
                payload = {
                    "target_type": target_type,
                    "target_key": effective_target,
                    **masked_details,
                }
                payload_str = json.dumps(payload, ensure_ascii=False)
                if sqlite:
                    sql = f"INSERT INTO {tbl} (ts, trace_id, event, payload) VALUES (CURRENT_TIMESTAMP, :trace_id, :event, :payload)"
                else:
                    sql = f"INSERT INTO {tbl} (ts, trace_id, event, payload) VALUES (now(), :trace_id, :event, CAST(:payload AS JSONB))"
                conn.execute(
                    text(sql),
                    {"trace_id": trace_id, "event": event, "payload": payload_str},
                )
            else:
                details_json_str = (
                    json.dumps(masked_details, ensure_ascii=False)
                    if masked_details
                    else None
                )

                # target_id が BIGINT/INTEGER カラムなので数値変換を試みる
                t_id_int = None
                try:
                    if effective_target is not None:
                        t_id_int = int(effective_target)
                except (ValueError, TypeError):
                    # 文字列ID → details_json に退避
                    if details_json_str is None:
                        details_json_str = json.dumps(
                            {"target_key": effective_target}, ensure_ascii=False
                        )
                    else:
                        d = masked_details.copy()
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
