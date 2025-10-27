import json
import logging
import os
import time
from datetime import timezone

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

# ===== ログ設定 =====
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)
log_sched = logging.getLogger("scheduler")
log_worker = logging.getLogger("worker")


# ===== DB エンジン =====
def make_engine():
    uri = os.getenv("DB_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not uri:
        raise RuntimeError("DB_URL / SQLALCHEMY_DATABASE_URI が未設定です")
    return create_engine(uri, future=True, pool_pre_ping=True)


# ====== Scheduler ======
def scheduler_loop():
    engine = make_engine()
    interval = int(os.getenv("SCHEDULER_INTERVAL_SEC", "10"))
    log_sched.info("Scheduler started. interval=%s", interval)
    while True:
        try:
            with engine.begin() as conn:
                now = conn.execute(text("select now()")).scalar()
                log_sched.info("tick now=%s", now)
                # 本来はここで「queued → scheduled」への移行などを行う
        except Exception as e:
            log_sched.exception("scheduler loop error: %s", e)
        time.sleep(interval)


# ====== Worker ======
def worker_loop():
    engine = make_engine()
    visibility_timeout = int(os.getenv("VISIBILITY_TIMEOUT_SEC", "1800"))
    log_worker.info("Worker started. visibility_timeout=%s", visibility_timeout)

    # result_json / error を JSONB として渡すためのステートメント（←ココが肝）
    stmt_success = text("""
        UPDATE public.jobs
           SET status = 'succeeded',
               result_json = :result,
               updated_at = now()
         WHERE id = :jid
    """).bindparams(
        bindparam("result", type_=JSONB),  # ← これで JSONB として安全に渡る
        bindparam("jid"),
    )

    stmt_error = text("""
        UPDATE public.jobs
           SET status = 'failed',
               error = :err,
               updated_at = now()
         WHERE id = :jid
    """).bindparams(
        bindparam("err", type_=JSONB),
        bindparam("jid"),
    )

    # ジョブのピック + ロック（行ロック）
    stmt_pick = text("""
        SELECT id, type, payload_json
          FROM public.jobs
         WHERE status = 'scheduled'
           AND next_run_at <= now()
         ORDER BY id
         FOR UPDATE SKIP LOCKED
         LIMIT 1
    """)

    # 実行中にする（必要なら attempts も加算）
    stmt_running = text("""
        UPDATE public.jobs
           SET status = 'running',
               attempts = attempts + 1,
               updated_at = now()
         WHERE id = :jid
    """)

    while True:
        try:
            with engine.begin() as conn:
                row = conn.execute(stmt_pick).mappings().first()
                if not row:
                    time.sleep(2)
                    continue

                jid = row["id"]
                jtype = row["type"]
                payload = row["payload_json"] or {}

                log_worker.info("picked job id=%s type=%s payload=%s", jid, jtype, payload)

                # 実行中に更新
                conn.execute(stmt_running, {"jid": jid})

                # ---- ここでジョブ実行（例: echo）----
                if jtype == "echo":
                    result = {
                        "ok": True,
                        "job_id": jid,
                        "echo": payload,
                        "trace_id": None,
                    }
                else:
                    # 未対応タイプは失敗扱い
                    raise RuntimeError(f"unknown job type: {jtype}")

                # 成功書き込み（JSONB として安全に保存）
                conn.execute(stmt_success, {"jid": jid, "result": result})
                log_worker.info("done id=%s status=succeeded", jid)

        except Exception as e:
            # 失敗時はエラーを書き込み（可能な限り jid を拾う）
            log_worker.exception("worker loop error: %s", e)
            try:
                # jid をエラーログから拾えないこともあるので best-effort
                jid_val = locals().get("jid")
                if jid_val:
                    err_obj = {"message": str(e)}
                    with engine.begin() as conn:
                        conn.execute(stmt_error, {"jid": jid_val, "err": err_obj})
            except Exception:
                # ここはほんとに最終手段なので握りつぶし
                pass

        time.sleep(2)


if __name__ == "__main__":
    # 簡易的に: 環境変数 MODE=worker なら worker、そうでなければ scheduler
    mode = os.getenv("MODE", "scheduler")
    if mode == "worker":
        worker_loop()
    else:
        scheduler_loop()

