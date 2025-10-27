from logging.config import fileConfig  # 使わないが互換のため残してOK
import logging
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

config = context.config

# INI ログは使わず固定の basicConfig で十分
logging.basicConfig(level=logging.INFO)

# DB URL を環境変数優先で注入
db_url = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = None  # 自動生成しない運用（スクリプトで明示的に書く想定）

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
