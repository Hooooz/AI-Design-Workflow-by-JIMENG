#!/usr/bin/env python3
"""
迁移本地项目数据到 Supabase 数据库
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from supabase import create_client


def get_supabase_client():
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        try:
            return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        except Exception as e:
            print(f"Supabase 连接失败: {e}")
            return None
    return None


def read_metadata(project_dir):
    meta_path = os.path.join(project_dir, "project_info.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def migrate_projects(project_names):
    client = get_supabase_client()
    if not client:
        print("无法连接到 Supabase")
        return

    root_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(root_dir, "projects")

    for project_name in project_names:
        project_dir = os.path.join(projects_dir, project_name)
        if not os.path.exists(project_dir):
            print(f"项目不存在: {project_name}")
            continue

        meta = read_metadata(project_dir)
        if meta:
            try:
                data = {
                    "project_name": project_name,
                    "brief": meta.get("brief", ""),
                    "model_name": meta.get("model_name", ""),
                    "creation_time": meta.get("creation_time", time.time()),
                    "status": meta.get("status", "completed"),
                    "current_step": meta.get("current_step", ""),
                    "tags": meta.get("tags", []),
                }
                result = client.table("projects").upsert(data).execute()
                print(f"✅ 已导入: {project_name}")
            except Exception as e:
                print(f"❌ 导入失败 {project_name}: {e}")
        else:
            print(f"⚠️ 无元数据: {project_name}")


if __name__ == "__main__":
    # 最新3个项目
    latest_projects = ["咖啡机概念设计3", "咖啡机概念设计2", "黑神话悟空手办"]

    print("开始迁移项目到 Supabase...")
    migrate_projects(latest_projects)
    print("完成!")
