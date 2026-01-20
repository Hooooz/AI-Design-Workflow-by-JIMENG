#!/usr/bin/env python3
"""
数据库迁移脚本 - 使用 postgresql 直接连接
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Supabase 连接信息
DB_HOST = "db.yojpsrakcqkyeaoxqlxg.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "需要你提供密码"  # 请填入密码


def migrate():
    print("连接数据库...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    migrations = [
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS market_analysis TEXT DEFAULT ''",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS visual_research TEXT DEFAULT ''",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS design_proposals TEXT DEFAULT ''",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS full_report TEXT DEFAULT ''",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'",
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            print(f"✅ 执行成功: {sql[:60]}...")
        except Exception as e:
            print(f"⚠️ {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n迁移完成!")


if __name__ == "__main__":
    migrate()
