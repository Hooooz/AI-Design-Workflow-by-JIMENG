import time
import hashlib
from typing import List, Dict, Any, Optional
import config

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                from supabase import create_client
                _supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            except Exception as e:
                print(f"Supabase 连接失败: {e}")
                _supabase_client = False
    return _supabase_client if _supabase_client else None

def get_project_id(project_name: str) -> str:
    """统一的项目 ID 生成逻辑 (MD5 12位)"""
    return hashlib.md5(project_name.encode()).hexdigest()[:12]

def fix_image_urls(images: List[str]) -> List[str]:
    """
    将路径转换为 Supabase 公网 URL。
    修复 Bug: 确保不对已经是 ID 的路径进行重复哈希。
    """
    if not images:
        return []

    supabase_url = config.SUPABASE_URL
    if not supabase_url:
        return images

    bucket = "project-images"
    fixed_images = []

    for img in images:
        if not img:
            continue

        # 处理旧的 IP 访问地址: http://47.89.249.90:8000/projects/{project_name}/{file}
        if "47.89.249.90" in img and "/projects/" in img:
            parts = img.split("/projects/")[-1].split("/")
            if len(parts) >= 2:
                # 提取项目名并生成 ID
                project_id = get_project_id(parts[0])
                filename = parts[1]
                fixed_images.append(f"{supabase_url}/storage/v1/object/public/{bucket}/{project_id}/{filename}")
                continue

        # 如果已经是正确的 Supabase 公网 URL，直接保留
        if img.startswith("http") and "supabase.co" in img:
            fixed_images.append(img)
            continue

        # 处理本地/相对路径格式: /projects/{project_id}/{filename}
        if img.startswith("/projects/"):
            parts = img.replace("/projects/", "").split("/")
            if len(parts) >= 2:
                segment = parts[0]
                # 智能识别：如果是12位16进制字符串，认为是ID；否则认为是项目名
                import re
                if re.match(r'^[0-9a-f]{12}$', segment):
                    project_id = segment
                else:
                    project_id = get_project_id(segment)

                filename = parts[1]
                fixed_images.append(f"{supabase_url}/storage/v1/object/public/{bucket}/{project_id}/{filename}")
            else:
                fixed_images.append(img)
        else:
            fixed_images.append(img)

    return fixed_images

def db_get_projects(limit: int = 50):
    client = get_supabase_client()
    if not client: return []
    try:
        result = client.table("projects").select("project_name, creation_time, status, current_step, tags, model_name, brief").order("creation_time", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []

def db_get_project(project_name: str):
    client = get_supabase_client()
    if not client: return None
    try:
        result = client.table("projects").select("*").eq("project_name", project_name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return None

def db_create_project(project_name: str, brief: str, model_name: str, tags: List[str] = None):
    client = get_supabase_client()
    if not client: return None
    try:
        data = {
            "project_name": project_name,
            "brief": brief,
            "model_name": model_name,
            "creation_time": time.time(),
            "status": "pending",
            "current_step": "",
            "tags": tags or [],
            "content": {},
        }
        result = client.table("projects").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"数据库插入失败: {e}")
        return None

def db_update_project(project_name: str, **kwargs):
    client = get_supabase_client()
    if not client: return None
    try:
        # 修正图片路径逻辑，如果更新的是 images，先运行 fix_image_urls
        if "images" in kwargs:
            kwargs["images"] = fix_image_urls(kwargs["images"])

        result = client.table("projects").update(kwargs).eq("project_name", project_name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"数据库更新失败: {e}")
        return None

def save_project_content(project_name: str, content: Dict[str, Any]):
    """更新项目文档内容"""
    return db_update_project(project_name, content=content)

def save_project_images(project_name: str, images: List[str]):
    """更新项目图片列表"""
    return db_update_project(project_name, images=images)
