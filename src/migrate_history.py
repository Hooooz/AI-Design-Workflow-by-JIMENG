import os
import sys
import json
import time

# 将 src 目录加入路径
sys.path.append(os.path.join(os.getcwd(), "src"))

from services import db_service

def migrate():
    projects_dir = "projects"
    if not os.path.exists(projects_dir):
        print("❌ 未找到本地 projects 目录")
        return

    local_projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
    print(f"📂 发现 {len(local_projects)} 个待迁移项目...\n")

    for project_name in local_projects:
        # 排除内部测试文件夹
        if project_name.startswith(("_", ".")): continue

        print(f"正在迁移: {project_name}")
        path = os.path.join(projects_dir, project_name)

        # 1. 读取元数据或创建默认元数据
        meta_path = os.path.join(path, "project_info.json")
        brief = ""
        model = "legacy-import"
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                try:
                    mdata = json.load(f)
                    brief = mdata.get("brief", "")
                    model = mdata.get("model_name", model)
                except: pass

        # 2. 读取各阶段文档
        content = {}
        files_map = {
            "1_Market_Analysis.md": "market_analysis",
            "2_Visual_Research.md": "visual_research",
            "3_Design_Proposals.json": "design_proposals",
            "Full_Design_Report.md": "full_report"
        }

        for filename, field in files_map.items():
            fpath = os.path.join(path, filename)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content[field] = f.read()

        # 3. 扫描图片
        images = []
        for f in os.listdir(path):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                # 记录为本地路径格式，db_service 会自动处理转换逻辑
                images.append(f"/projects/{project_name}/{f}")

        # 4. 同步到 Supabase
        existing = db_service.db_get_project(project_name)
        if not existing:
            print(f"  - 创建新云端项目...")
            db_service.db_create_project(project_name, brief, model)

        db_service.db_update_project(project_name, content=content, images=images, status="completed")
        print(f"  ✅ 迁移完成\n")

    print("🎉 所有历史数据已成功找回并同步至 Supabase！")

if __name__ == "__main__":
    migrate()
