#!/usr/bin/env python3
"""
一键上传单个本地项目到 Supabase
用于演示和数据恢复
"""
import os
import sys
import json
import hashlib

# 强制设置环境变量（解决 .env 加载时机问题）
os.environ["SUPABASE_URL"] = "https://yojpsrakcqkyeaoxqlxg.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvanBzcmFrY3FreWVhb3hxbHhnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODU5OTAwMCwiZXhwIjoyMDg0MTc1MDAwfQ.02BG69I60C27J4YPVtCtS-6uGZ5HFwoU23W4YhN2eDY"

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services import db_service
import config

def get_project_id(project_name: str) -> str:
    """生成项目 ID（MD5 12位）"""
    return hashlib.md5(project_name.encode()).hexdigest()[:12]

def upload_project(project_name: str):
    """上传指定项目到 Supabase"""

    print(f"\n🚀 开始上传项目: {project_name}")
    print("=" * 60)

    project_path = os.path.join("projects", project_name)

    if not os.path.exists(project_path):
        print(f"❌ 项目目录不存在: {project_path}")
        return False

    # 1. 读取项目元数据
    meta_path = os.path.join(project_path, "project_info.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            brief = meta.get("brief", "")
            model_name = meta.get("model_name", "gemini-2.0-flash-exp")
            creation_time = meta.get("creation_time", 0)
    else:
        brief = ""
        model_name = "legacy-upload"
        creation_time = 0

    # 2. 检查项目是否已存在
    existing = db_service.db_get_project(project_name)

    if not existing:
        print(f"📝 创建新项目记录...")
        new_proj = db_service.db_create_project(
            project_name=project_name,
            brief=brief,
            model_name=model_name
        )
        if not new_proj:
            print("❌ 创建项目失败")
            return False
        print(f"✅ 项目创建成功")
    else:
        print(f"ℹ️  项目已存在，准备更新内容")

    # 3. 读取文档内容
    content = {}

    # 市场分析
    ma_path = os.path.join(project_path, "1_Market_Analysis.md")
    if os.path.exists(ma_path):
        with open(ma_path, "r", encoding="utf-8") as f:
            content["market_analysis"] = f.read()
        print(f"  ✅ 市场分析 ({len(content['market_analysis'])} 字符)")

    # 视觉研究
    vr_path = os.path.join(project_path, "2_Visual_Research.md")
    if os.path.exists(vr_path):
        with open(vr_path, "r", encoding="utf-8") as f:
            content["visual_research"] = f.read()
        print(f"  ✅ 视觉研究 ({len(content['visual_research'])} 字符)")

    # 设计方案（JSON）
    dp_path = os.path.join(project_path, "3_Design_Proposals.json")
    if os.path.exists(dp_path):
        with open(dp_path, "r", encoding="utf-8") as f:
            content["design_proposals"] = f.read()
        print(f"  ✅ 设计方案 ({len(content['design_proposals'])} 字符)")

    # 完整报告
    fr_path = os.path.join(project_path, "Full_Design_Report.md")
    if os.path.exists(fr_path):
        with open(fr_path, "r", encoding="utf-8") as f:
            content["full_report"] = f.read()
        print(f"  ✅ 完整报告 ({len(content['full_report'])} 字符)")

    # 更新文档内容
    db_service.db_update_project(project_name, content=content)

    # 4. 上传图片到 Supabase Storage
    print(f"\n📤 上传图片到 Supabase Storage...")

    from supabase import create_client
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    project_id = get_project_id(project_name)
    bucket = "project-images"

    image_urls = []

    for filename in os.listdir(project_path):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            local_path = os.path.join(project_path, filename)
            storage_path = f"{project_id}/{filename}"

            try:
                with open(local_path, "rb") as f:
                    file_bytes = f.read()

                # 上传到 Supabase Storage
                supabase.storage.from_(bucket).upload(
                    storage_path,
                    file_bytes,
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )

                # 生成公网 URL
                public_url = f"{config.SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
                image_urls.append(public_url)

                print(f"  ✅ {filename} → {storage_path}")

            except Exception as e:
                print(f"  ⚠️  {filename} 上传失败: {e}")

    # 5. 更新图片 URL 列表
    if image_urls:
        db_service.db_update_project(project_name, images=image_urls)
        print(f"\n✅ 共上传 {len(image_urls)} 张图片")

    # 6. 标记为已完成
    db_service.db_update_project(project_name, status="completed", current_step="")

    print("\n" + "=" * 60)
    print(f"🎉 项目上传完成！")
    print(f"📊 项目名称: {project_name}")
    print(f"📝 文档字段: {len(content)} 个")
    print(f"🖼️  图片数量: {len(image_urls)} 张")
    print(f"🔗 访问地址: https://ai-design-workflow-by-jimeng.vercel.app")
    print("=" * 60 + "\n")

    return True

if __name__ == "__main__":
    # 上传"拍立得包包"项目
    upload_project("拍立得包包")
