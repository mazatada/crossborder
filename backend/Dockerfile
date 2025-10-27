FROM python:3.11-slim

WORKDIR /app

# 依存を先に入れる
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# アプリ本体をコピー
COPY app /app/app

# エントリポイント（存在する場合）
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh || true

ENV PYTHONUNBUFFERED=1

# backend サービス用（worker/scheduler は compose 側の command で上書き）
CMD ["bash", "/entrypoint.sh"]

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
