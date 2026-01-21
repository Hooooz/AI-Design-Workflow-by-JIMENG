#!/usr/bin/env python3
"""
迁移脚本：将现有项目的图片路径保存到 Supabase 数据库
运行方式: railway run python migrate_images.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import db_get_projects, db_update_project, get_supabase_client


def migrate_images():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_dir = os.path.join(root_dir, "projects")

    projects = db_get_projects()
    print(f"Found {len(projects)} projects in database")

    for project in projects:
        project_name = project.get("project_name")
        project_dir = os.path.join(projects_dir, project_name)

        if not os.path.exists(project_dir):
            print(f"  {project_name}: 文件夹不存在，跳过")
            continue

        # Scan images from filesystem
        images = []
        for f in os.listdir(project_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                images.append(f"/projects/{project_name}/{f}")

        if images:
            # Sort by modification time
            images.sort(
                key=lambda x: os.path.getmtime(
                    os.path.join(project_dir, os.path.basename(x))
                ),
                reverse=True,
            )

            # Update database with images
            db_update_project(project_name, images=images)
            print(f"  {project_name}: 已保存 {len(images)} 张图片到数据库")
        else:
            print(f"  {project_name}: 没有图片")

    print("迁移完成！")


if __name__ == "__main__":
    migrate_images()
