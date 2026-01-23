#!/usr/bin/env python3
"""
验证 Supabase 数据是否正确写入
"""
import os
import sys

# 强制设置环境变量
os.environ["SUPABASE_URL"] = "https://yojpsrakcqkyeaoxqlxg.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvanBzcmFrY3FreWVhb3hxbHhnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODU5OTAwMCwiZXhwIjoyMDg0MTc1MDAwfQ.02BG69I60C27J4YPVtCtS-6uGZ5HFwoU23W4YhN2eDY"

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services import db_service
import json

def verify_project():
    """验证项目数据"""

    print("🔍 正在查询 Supabase 数据库...")
    print("=" * 60)

    project = db_service.db_get_project("拍立得包包")

    if not project:
        print("❌ 项目不存在！")
        return

    print(f"✅ 找到项目: {project.get('project_name')}\n")

    # 检查各字段
    fields = {
        "brief": "需求描述",
        "market_analysis": "市场分析",
        "visual_research": "视觉研究",
        "design_proposals": "设计方案",
        "full_report": "完整报告",
        "images": "图片列表",
        "content": "文档内容(JSON)",
        "status": "状态",
        "model_name": "模型名称"
    }

    print("📊 字段检查:\n")
    for field, desc in fields.items():
        value = project.get(field)
        if value:
            if isinstance(value, str):
                length = len(value)
                preview = value[:50] + "..." if length > 50 else value
                print(f"  ✅ {desc} ({field}): {length} 字符")
                print(f"     预览: {preview}\n")
            elif isinstance(value, list):
                print(f"  ✅ {desc} ({field}): {len(value)} 项")
                for item in value[:2]:
                    print(f"     - {item}")
                print()
            elif isinstance(value, dict):
                print(f"  ✅ {desc} ({field}): {len(value)} 个键")
                print(f"     键: {list(value.keys())}\n")
            else:
                print(f"  ✅ {desc} ({field}): {value}\n")
        else:
            print(f"  ❌ {desc} ({field}): 空\n")

    # 详细输出 content 字段
    if project.get("content"):
        print("\n📄 Content 字段详细内容:")
        content = project["content"]
        if isinstance(content, dict):
            for key, val in content.items():
                if isinstance(val, str):
                    print(f"  - {key}: {len(val)} 字符")
                else:
                    print(f"  - {key}: {val}")

    # 输出完整 JSON（用于调试）
    print("\n" + "=" * 60)
    print("📝 完整数据（JSON）:\n")
    print(json.dumps(project, ensure_ascii=False, indent=2)[:2000] + "\n...(truncated)")

if __name__ == "__main__":
    verify_project()
