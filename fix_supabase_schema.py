#!/usr/bin/env python3
"""
Supabase 数据库结构修复脚本
自动添加缺失的列并修复表结构
"""
import os
from supabase import create_client

# Supabase 凭证
SUPABASE_URL = "https://yojpsrakcqkyeaoxqlxg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvanBzcmFrY3FreWVhb3hxbHhnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODU5OTAwMCwiZXhwIjoyMDg0MTc1MDAwfQ.02BG69I60C27J4YPVtCtS-6uGZ5HFwoU23W4YhN2eDY"

def fix_database_schema():
    """修复 Supabase 数据库表结构"""

    print("🔧 开始修复 Supabase 数据库结构...")
    print("=" * 60)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 需要执行的 SQL 语句列表
    sql_commands = [
        # 1. 添加 content 列（存储文档内容）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS content JSONB DEFAULT '{}'::jsonb;
        """,

        # 2. 添加 images 列（存储图片 URL 数组）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'::jsonb;
        """,

        # 3. 添加 market_analysis 列（市场分析文本）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS market_analysis TEXT DEFAULT '';
        """,

        # 4. 添加 visual_research 列（视觉研究文本）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS visual_research TEXT DEFAULT '';
        """,

        # 5. 添加 design_proposals 列（设计方案 JSON）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS design_proposals TEXT DEFAULT '';
        """,

        # 6. 添加 full_report 列（完整报告文本）
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS full_report TEXT DEFAULT '';
        """,

        # 7. 确保 tags 列存在
        """
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
        """,
    ]

    print("\n📝 执行 SQL 命令...")

    for i, sql in enumerate(sql_commands, 1):
        try:
            # Supabase Python SDK 使用 rpc 执行原始 SQL
            result = supabase.rpc('exec_sql', {'query': sql}).execute()
            print(f"  ✅ 命令 {i}/{len(sql_commands)} 执行成功")
        except Exception as e:
            # 如果 RPC 不可用，尝试使用 PostgREST 的 query 方法
            print(f"  ⚠️  命令 {i}/{len(sql_commands)} 需要手动执行（SDK 限制）")
            print(f"     错误: {e}")

    print("\n" + "=" * 60)
    print("✅ 数据库结构修复完成！")
    print("\n📋 如果出现 SDK 限制错误，请在 Supabase 控制台手动执行以下 SQL：")
    print("-" * 60)
    print("""
-- 添加所有缺失的列
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS content JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS market_analysis TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS visual_research TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS design_proposals TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS full_report TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
    """)
    print("-" * 60)

    # 验证表结构
    print("\n🔍 验证当前表结构...")
    try:
        result = supabase.table("projects").select("*").limit(1).execute()
        if result.data:
            columns = result.data[0].keys()
            print(f"  ✅ 当前表包含 {len(columns)} 列:")
            for col in sorted(columns):
                print(f"     - {col}")
        else:
            print("  ℹ️  表为空，无法验证列结构")
    except Exception as e:
        print(f"  ⚠️  验证失败: {e}")

if __name__ == "__main__":
    fix_database_schema()
