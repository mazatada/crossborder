#!/usr/bin/env python3
"""
ERD (Entity Relationship Diagram) Generator

SQLAlchemyモデルからERDとDDLを生成するスクリプト
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import (
    Job, MediaBlob, AuditEvent, PNSubmission, 
    DocumentPackage, WebhookEndpoint, OrderStatus, WebhookDLQ
)
from app.db import db
from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CreateTable


def generate_erd_markdown():
    """Generate ERD in Markdown format"""
    
    erd = """# Entity Relationship Diagram (ERD)

データベーススキーマの概要

---

## テーブル一覧

### 1. jobs
ジョブ管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | BigInteger | NO | AUTO | ジョブID |
| type | String(16) | NO | - | ジョブタイプ (pack, pn, etc) |
| status | String(16) | NO | - | ステータス (pending, running, done, failed) |
| trace_id | String(64) | YES | - | トレースID |
| error | JSON | YES | - | エラー情報 |
| attempts | Integer | NO | 0 | 試行回数 |
| next_run_at | DateTime | YES | - | 次回実行時刻 |
| payload_json | JSON | YES | - | ジョブペイロード |
| result_json | JSON | YES | - | 実行結果 |
| created_at | DateTime | NO | NOW | 作成日時 |
| updated_at | DateTime | NO | NOW | 更新日時 |

**インデックス**: status, trace_id

---

### 2. media_blobs
メディアファイル管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| media_id | String(128) | NO | - | メディアID (PK) |
| sha256 | String(64) | NO | - | SHA256ハッシュ |
| size | Integer | NO | - | ファイルサイズ |
| mime | String(64) | NO | application/octet-stream | MIMEタイプ |
| created_at | DateTime | NO | NOW | 作成日時 |

---

### 3. audit_events
監査ログテーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | イベントID |
| trace_id | String(64) | NO | - | トレースID |
| event | String(64) | NO | - | イベント名 |
| payload | JSON | YES | - | イベントデータ |
| ts | DateTime | NO | NOW | タイムスタンプ |

**インデックス**: trace_id

---

### 4. pn_submissions
PN提出管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | 提出ID |
| trace_id | String(64) | NO | - | トレースID |
| product | JSON | NO | - | 商品情報 |
| logistics | JSON | NO | - | 物流情報 |
| importer | JSON | NO | - | 輸入者情報 |
| consignee | JSON | NO | - | 荷受人情報 |
| label_media_id | String(128) | YES | - | ラベルメディアID |
| created_at | DateTime | NO | NOW | 作成日時 |

**インデックス**: trace_id

---

### 5. document_packages
書類パッケージ管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | パッケージID |
| trace_id | String(64) | NO | - | トレースID |
| hs_code | String(16) | NO | - | HSコード |
| required_uom | String(8) | NO | - | 必要単位 |
| invoice_uom | String(8) | NO | - | インボイス単位 |
| invoice_payload | JSON | YES | - | インボイスデータ |
| created_at | DateTime | NO | NOW | 作成日時 |

**インデックス**: trace_id

---

### 6. webhook_endpoints
Webhookエンドポイント管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | エンドポイントID |
| url | String(512) | NO | - | WebhookURL |
| secret | String(128) | NO | - | HMAC署名用シークレット |
| events | JSON | NO | - | 購読イベントリスト |
| active | Boolean | NO | TRUE | 有効フラグ |
| created_at | DateTime | NO | NOW | 作成日時 |
| updated_at | DateTime | NO | NOW | 更新日時 |

---

### 7. order_statuses
注文ステータス管理テーブル

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | ステータスID |
| order_id | String(128) | NO | - | 注文ID |
| status | String(32) | NO | - | ステータス (PAID, CANCELED) |
| ts | DateTime | NO | - | 外部システムのタイムスタンプ |
| customer_region | String(64) | YES | - | 顧客地域 |
| created_at | DateTime | NO | NOW | 作成日時 |

**インデックス**: order_id

---

### 8. webhook_dlq
Webhook Dead Letter Queue

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|-----|------|-----------|------|
| id | Integer | NO | AUTO | DLQエントリID |
| webhook_id | Integer | NO | - | WebhookエンドポイントID (FK) |
| event_type | String(64) | NO | - | イベントタイプ |
| payload | JSON | NO | - | イベントペイロード |
| trace_id | String(64) | YES | - | トレースID |
| attempts | Integer | NO | 0 | 試行回数 |
| last_error | Text | YES | - | 最後のエラー |
| last_status_code | Integer | YES | - | 最後のステータスコード |
| replayed | Boolean | NO | FALSE | リプレイ済みフラグ |
| created_at | DateTime | NO | NOW | 作成日時 |
| expires_at | DateTime | NO | - | 有効期限 (72時間) |

**インデックス**: trace_id  
**外部キー**: webhook_id → webhook_endpoints.id

---

## リレーションシップ

```mermaid
erDiagram
    webhook_endpoints ||--o{ webhook_dlq : "has many"
    
    webhook_endpoints {
        int id PK
        string url
        string secret
        json events
        boolean active
    }
    
    webhook_dlq {
        int id PK
        int webhook_id FK
        string event_type
        json payload
        string trace_id
        int attempts
        datetime expires_at
    }
    
    jobs {
        bigint id PK
        string type
        string status
        string trace_id
        json payload_json
    }
    
    audit_events {
        int id PK
        string trace_id
        string event
        json payload
    }
    
    pn_submissions {
        int id PK
        string trace_id
        json product
        json logistics
    }
    
    document_packages {
        int id PK
        string trace_id
        string hs_code
    }
    
    order_statuses {
        int id PK
        string order_id
        string status
    }
```

---

## インデックス戦略

- **trace_id**: 全テーブルで検索頻度が高いためインデックス化
- **status**: ジョブテーブルでステータスフィルタリングに使用
- **order_id**: 注文ステータステーブルで検索に使用

---

最終更新: 2025-12-05
"""
    
    return erd


def generate_ddl():
    """Generate DDL (Data Definition Language)"""
    
    # テスト用のインメモリデータベースを使用
    engine = create_engine('sqlite:///:memory:')
    metadata = MetaData()
    
    # 全テーブルのDDLを生成
    ddl_statements = []
    
    for table in [
        Job.__table__,
        MediaBlob.__table__,
        AuditEvent.__table__,
        PNSubmission.__table__,
        DocumentPackage.__table__,
        WebhookEndpoint.__table__,
        OrderStatus.__table__,
        WebhookDLQ.__table__
    ]:
        create_table = CreateTable(table)
        ddl_statements.append(str(create_table.compile(engine)))
    
    return '\n\n'.join(ddl_statements)


def main():
    """メイン処理"""
    
    # ERDをMarkdown形式で生成
    erd_markdown = generate_erd_markdown()
    
    # ERDファイルに書き出し
    erd_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'erd.md')
    with open(erd_path, 'w', encoding='utf-8') as f:
        f.write(erd_markdown)
    
    print(f"✓ ERD generated: {erd_path}")
    
    # DDLを生成
    ddl = generate_ddl()
    
    # DDLファイルに書き出し
    ddl_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'schema.sql')
    with open(ddl_path, 'w', encoding='utf-8') as f:
        f.write("-- Auto-generated DDL\n")
        f.write("-- Generated at: 2025-12-05\n\n")
        f.write(ddl)
    
    print(f"✓ DDL generated: {ddl_path}")
    print("\nDone!")


if __name__ == '__main__':
    main()
