#!/usr/bin/env python3
"""
修复数据结构：将 content 中的字段提取到顶层
"""
import os
import sys

os.environ["SUPABASE_URL"] = "https://yojpsrakcqkyeaoxqlxg.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvanBzcmFrY3FreWVhb3hxbHhnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODU5OTAwMCwiZXhwIjoyMDg0MTc1MDAwfQ.02BG69I60C27J4YPVtCtS-6uGZ5HFwoU23W4YhN2eDY"

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services import db_service

def fix_data_structure():
    """将 content 字段中的数据提取到顶层字段"""

    print("🔧 开始修复数据结构...")
    print("=" * 60)

    # 获取项目
    project = db_service.db_get_project("拍立得包包")

    if not project:
        print("❌ 项目不存在")
        return False

    print(f"✅ 找到项目: {project['project_name']}\n")

    # 检查 content 字段
    content = project.get("content", {})

    if not content:
        print("❌ content 字段为空")
        return False

    print(f"📦 content 字段包含: {list(content.keys())}\n")

    # 提取字段到顶层
    update_data = {}

    fields_to_extract = ["market_analysis", "visual_research", "design_proposals", "full_report"]

    for field in fields_to_extract:
        if field in content and content[field]:
            update_data[field] = content[field]
            print(f"  ✅ 提取 {field}: {len(content[field])} 字符")

    # 更新数据库
    if update_data:
        print(f"\n📤 正在更新数据库...")
        result = db_service.db_update_project("拍立得包包", **update_data)

        if result:
            print(f"✅ 数据库更新成功！\n")
            print("=" * 60)
            print("🎉 修复完成！现在前端应该能正常显示了")
            print("🔗 访问：https://ai-design-workflow-by-jimeng.vercel.app")
            print("=" * 60)
            return True
        else:
            print("❌ 数据库更新失败")
            return False
    else:
        print("⚠️  没有需要提取的数据")
        return False

if __name__ == "__main__":
    fix_data_structure()
