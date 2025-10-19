FROM python:3.11-slim

WORKDIR /app

# 依存関係を先にインストール（キャッシュ効くように）
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# アプリ本体をコピー
COPY backend/app /app/app
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV FLASK_APP=app.factory \
    PYTHONUNBUFFERED=1

EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
