#!/bin/sh
set -eu

# 環境変数の可視化（未設定時は '(unset)' と表示）
echo "[entrypoint] SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI:-'(unset)'}"

# ---- DB起動待ち（Postgresのみ待機、SQLiteならスキップ） ----
python3 - <<'PY'
import os, time, sys
uri = os.environ.get("SQLALCHEMY_DATABASE_URI", "")

# SQLAlchemy方言付きURIをpsycopgが読める形へ（例: postgresql+psycopg:// → postgresql://）
if uri.startswith("postgresql+psycopg://"):
    uri = "postgresql://" + uri.split("postgresql+psycopg://", 1)[1]

if uri.startswith("postgresql://"):
    import psycopg
    for i in range(30):
        try:
            with psycopg.connect(uri) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    print("DB OK")
                    break
        except Exception as e:
            print(f"DB not ready ({i+1}/30): {e}")
            time.sleep(1)
    else:
        print("DB NOT READY, giving up", file=sys.stderr)
        sys.exit(1)
else:
    print("SQLite mode or URI unset; skipping DB wait")
PY

# ---- Flask 起動 ----
export FLASK_APP=app.factory
echo "[entrypoint] starting flask..."
exec python -m flask run --host=0.0.0.0 --port=5000
