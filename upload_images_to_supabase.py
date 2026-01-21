#!/usr/bin/env python3
"""
上传本地图片到 Supabase Storage（只处理线上项目）
通过 Railway 后端 API 获取项目列表
"""

import os
import sys
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SUPABASE_URL = "https://yojpsrakcqkyeaoxqlxg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvanBzcmFrY3FreWVhb3hxbHhnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODU5OTAwMCwiZXhwIjoyMDg0MTc1MDAwfQ.02BG69I60C27J4YPVtCtS-6uGZ5HFwoU23W4YhN2eDY"
BUCKET_NAME = "project-images"
API_URL = "https://web-production-d9bfe.up.railway.app"


def create_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_online_projects(session):
    """通过 Railway 后端 API 获取线上项目列表"""
    try:
        response = session.get(f"{API_URL}/api/projects", timeout=30)
        if response.status_code == 200:
            data = response.json()
            return [p.get("project_name") for p in data if p and p.get("project_name")]
        return []
    except Exception as e:
        print(f"❌ 获取线上项目失败: {e}")
        return []


def upload_image(session, local_path, project_name, filename):
    for attempt in range(3):
        try:
            file_path = f"{project_name}/{filename}"
            url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_path}"

            with open(local_path, "rb") as f:
                file_data = f.read()

            headers = {
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "image/jpeg",
            }

            response = session.post(url, headers=headers, data=file_data, timeout=180)

            if response.status_code in [200, 201]:
                public_url = (
                    f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
                )
                return public_url
            elif response.status_code == 400:
                public_url = (
                    f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
                )
                check = session.head(public_url, timeout=10)
                if check.status_code == 200:
                    return public_url
            else:
                print(f"    尝试 {attempt + 1}: {response.status_code}")

        except Exception as e:
            print(f"    尝试 {attempt + 1}: {str(e)[:50]}")

        time.sleep(3)

    return None


def main():
    print("🚀 开始上传图片到 Supabase Storage...\n")

    session = create_session()
    online_projects = get_online_projects(session)

    print(f"📡 线上共有 {len(online_projects)} 个项目:\n")
    for name in online_projects:
        print(f"   - {name}")
    print()

    root_dir = "/Users/huangchuhao/Downloads/AI 工具/Cursor 代码库/Howie AI 工作室/彩友乐 AI 提效/AI设计工作流"
    projects_dir = os.path.join(root_dir, "projects")

    if not os.path.exists(projects_dir):
        print("❌ projects 目录不存在")
        return

    total_uploaded = 0
    total_skipped = 0

    for project_name in online_projects:
        project_dir = os.path.join(projects_dir, project_name)

        if not os.path.exists(project_dir):
            print(f"📂 {project_name}: 本地文件夹不存在，跳过")
            continue

        images = [
            f
            for f in os.listdir(project_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if not images:
            print(f"📂 {project_name}: 无图片，跳过")
            continue

        print(f"📂 {project_name}: {len(images)} 张图片")

        image_urls_map = {}

        for filename in sorted(images):
            local_path = os.path.join(project_dir, filename)

            check_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{project_name}/{filename}"
            try:
                check = session.head(check_url, timeout=15)
                if check.status_code == 200:
                    print(f"  ⏭️ {filename} 已存在")
                    image_urls_map[filename] = check_url
                    total_skipped += 1
                    continue
            except:
                pass

            public_url = upload_image(session, local_path, project_name, filename)
            if public_url:
                print(f"  ✅ {filename}")
                image_urls_map[filename] = public_url
                total_uploaded += 1
            else:
                print(f"  ❌ {filename}")

            time.sleep(1)

        if image_urls_map:
            images_with_times = []
            for filename, url in image_urls_map.items():
                local_path = os.path.join(project_dir, filename)
                mtime = os.path.getmtime(local_path)
                images_with_times.append((mtime, url))

            images_with_times.sort(key=lambda x: x[0], reverse=True)
            image_urls = [url for _, url in images_with_times]

            # 通过 Railway API 更新数据库
            try:
                project_data = session.get(
                    f"{API_URL}/api/project/{project_name}", timeout=30
                ).json()
                if "metadata" in project_data:
                    content = project_data["metadata"].get("content", {})
                    design_proposals = content.get("design_proposals", "")

                    if design_proposals and design_proposals.startswith("{"):
                        dp = json.loads(design_proposals)
                        if "prompts" in dp:
                            for prompt in dp["prompts"]:
                                orig_path = prompt.get("image_path", "")
                                if orig_path and orig_path.startswith("/projects/"):
                                    filename = os.path.basename(orig_path)
                                    if filename in image_urls_map:
                                        prompt["image_path"] = image_urls_map[filename]

                            content["design_proposals"] = json.dumps(
                                dp, ensure_ascii=False, indent=2
                            )

                            # 这里无法直接更新数据库，需要 Railway 后端处理
                            print(f"  📝 图片路径需要更新到 design_proposals")
            except Exception as e:
                print(f"    警告: 无法更新 design_proposals: {e}")

            print()

    print(f"\n🎉 完成！共上传 {total_uploaded} 张，跳过 {total_skipped} 张")
    print("\n注意: design_proposals 中的图片路径需要在 Railway 后端更新")


if __name__ == "__main__":
    main()
