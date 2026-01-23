#!/usr/bin/env python3
"""
Supabase 数据库结构修复脚本（直连 PostgreSQL）
使用数据库密码直接修改表结构
"""
import psycopg2

# Supabase PostgreSQL 连接信息（使用 Session Pooler，端口 6543，IPv4 兼容）
DB_CONFIG = {
    "host": "db.yojpsrakcqkyeaoxqlxg.supabase.co",
    "port": 6543,  # Session Pooler 端口（IPv4 兼容）
    "database": "postgres",
    "user": "postgres.yojpsrakcqkyeaoxqlxg",  # Pooler 需要完整的用户名
    "password": "BQvrKNQNV3lnLNPu"
}

def fix_database_schema():
    """通过直连 PostgreSQL 修复表结构"""

    print("🔧 开始修复 Supabase 数据库结构（直连模式）...")
    print("=" * 60)

    try:
        # 连接数据库
        print("📡 正在连接 PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        print("  ✅ 数据库连接成功\n")

        # 执行表结构修改
        sql_commands = [
            ("添加 images 列", """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'::jsonb;
            """),
            ("添加 market_analysis 列", """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS market_analysis TEXT DEFAULT '';
            """),
            ("添加 visual_research 列", """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS visual_research TEXT DEFAULT '';
            """),
            ("添加 design_proposals 列", """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS design_proposals TEXT DEFAULT '';
            """),
            ("添加 full_report 列", """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS full_report TEXT DEFAULT '';
            """),
        ]

        print("📝 执行表结构修改...\n")

        for i, (desc, sql) in enumerate(sql_commands, 1):
            try:
                cursor.execute(sql)
                print(f"  ✅ [{i}/{len(sql_commands)}] {desc}")
            except Exception as e:
                print(f"  ⚠️  [{i}/{len(sql_commands)}] {desc} - 错误: {e}")

        # 验证表结构
        print("\n🔍 验证修复结果...\n")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'projects'
            ORDER BY column_name;
        """)

        columns = cursor.fetchall()
        print(f"  ✅ 'projects' 表当前包含 {len(columns)} 列:\n")

        required_columns = ['images', 'market_analysis', 'visual_research', 'design_proposals', 'full_report']
        found_columns = {col[0]: col[1] for col in columns}

        for col_name in required_columns:
            if col_name in found_columns:
                print(f"     ✅ {col_name} ({found_columns[col_name]})")
            else:
                print(f"     ❌ {col_name} - 缺失")

        # 关闭连接
        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("🎉 数据库结构修复完成！")
        print("=" * 60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ 数据库操作失败: {e}")
        return False

if __name__ == "__main__":
    if fix_database_schema():
        print("✅ 现在可以重新运行上传脚本了！")
        print("   执行命令: python3 upload_single_project.py")
    else:
        print("❌ 修复失败，请检查错误信息")
