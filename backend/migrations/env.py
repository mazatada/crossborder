import os, sys
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# 環境変数で URL 上書き（docker/ローカル両対応）
uri = os.getenv("SQLALCHEMY_DATABASE_URI")
if uri:
    config.set_main_option("sqlalchemy.url", uri)

# ログ設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# プロジェクトルートを import path に追加
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# Alembic 実行フラグ：create_app 内の副作用を避ける
os.environ["ALEMBIC_RUNNING"] = "1"

from app.factory import create_app
from app.db import db

app = create_app()
app.app_context().push()

# ★ モデルを明示 import（autogenerate が空になるのを防ぐ）
import app.models as _models  # noqa: F401

target_metadata = db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",          # ← ここが必須！
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
