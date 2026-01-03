#!/usr/bin/env python3
"""
ERD (Entity Relationship Diagram) Generator

SQLAlchemyモデルからERDとDDLを生成するスクリプト
"""
import sys
import os
from typing import List
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import (
    Job,
    MediaBlob,
    AuditEvent,
    PNSubmission,
    DocumentPackage,
    WebhookEndpoint,
    OrderStatus,
    WebhookDLQ,
)
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable


TABLES = [
    Job.__table__,
    MediaBlob.__table__,
    AuditEvent.__table__,
    PNSubmission.__table__,
    DocumentPackage.__table__,
    WebhookEndpoint.__table__,
    OrderStatus.__table__,
    WebhookDLQ.__table__,
]


def _format_default(column) -> str:
    if column.default is not None:
        return str(column.default.arg)
    if column.server_default is not None:
        return str(column.server_default.arg)
    return "-"


def _format_constraints(column) -> str:
    flags: List[str] = []
    if column.primary_key:
        flags.append("PK")
    if column.unique:
        flags.append("UNIQUE")
    if column.foreign_keys:
        refs = [fk.target_fullname for fk in column.foreign_keys]
        flags.append("FK->" + ",".join(refs))
    return ", ".join(flags) if flags else "-"


def _render_table_markdown(table) -> str:
    lines = []
    lines.append(f"### {table.name}")
    lines.append("| カラム名 | 型 | NULL | デフォルト | 制約 |")
    lines.append("|---------|-----|------|-----------|------|")
    for col in table.columns:
        col_type = str(col.type)
        nullable = "YES" if col.nullable else "NO"
        default = _format_default(col)
        constraints = _format_constraints(col)
        lines.append(f"| {col.name} | {col_type} | {nullable} | {default} | {constraints} |")
    return "\n".join(lines)


def _render_indexes_markdown(table) -> str:
    if not table.indexes:
        return ""
    idx_lines = ["**インデックス**:"]
    for idx in table.indexes:
        cols = ",".join(c.name for c in idx.columns)
        idx_lines.append(f"- {idx.name}: {cols}")
    return "\n".join(idx_lines)


def _render_mermaid_relationships() -> str:
    rel_lines = ["```mermaid", "erDiagram"]
    for table in TABLES:
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            child = table.name
            rel_lines.append(f"    {parent} ||--o{{ {child} : \"fk\"")
    rel_lines.append("```")
    return "\n".join(rel_lines)


def generate_erd_markdown():
    """Generate ERD in Markdown format"""

    erd = """# Entity Relationship Diagram (ERD)

データベーススキーマの概要

---

## テーブル一覧

"""

    table_sections = []
    for table in TABLES:
        table_sections.append(_render_table_markdown(table))
        idx_section = _render_indexes_markdown(table)
        if idx_section:
            table_sections.append(idx_section)
        table_sections.append("\n---\n")

    relations = _render_mermaid_relationships()
    footer = "\n## リレーションシップ\n\n" + relations + "\n"

    return erd + "\n".join(table_sections) + footer


def generate_ddl():
    """Generate DDL (Data Definition Language)"""
    
    # テスト用のインメモリデータベースを使用
    engine = create_engine('sqlite:///:memory:')
    # 全テーブルのDDLを生成
    ddl_statements = []
    
    for table in TABLES:
        create_table = CreateTable(table)
        ddl_statements.append(str(create_table.compile(engine)))
    
    return '\n\n'.join(ddl_statements)


def main():
    """メイン処理"""
    
    # ERDをMarkdown形式で生成
    erd_markdown = generate_erd_markdown()
    
    # 出力先ディレクトリの決定 (Docker/Local両対応)
    base_dir = os.path.dirname(__file__)
    # ローカル環境: scriptsの兄弟にbackendがある
    target_dir = os.path.join(base_dir, '..', 'backend')
    if not os.path.exists(target_dir):
        # Docker環境: scriptsの親(/app)がbackendそのもの
        target_dir = os.path.join(base_dir, '..')
    
    # ERDファイルに書き出し
    erd_path = os.path.join(target_dir, 'erd.md')
    with open(erd_path, 'w', encoding='utf-8') as f:
        f.write(erd_markdown)
    
    print(f"✓ ERD generated: {erd_path}")
    
    # DDLを生成
    ddl = generate_ddl()
    
    # DDLファイルに書き出し
    ddl_path = os.path.join(target_dir, 'schema.sql')
    with open(ddl_path, 'w', encoding='utf-8') as f:
        f.write("-- Auto-generated DDL\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(ddl)
    
    print(f"✓ DDL generated: {ddl_path}")
    print("\nDone!")


if __name__ == '__main__':
    main()
