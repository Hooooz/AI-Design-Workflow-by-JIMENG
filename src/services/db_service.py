import time
import hashlib
from typing import List, Dict, Any, Optional
from config import logger
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
                logger.error(f"Supabase 连接失败: {e}")
                _supabase_client = False
    return _supabase_client if _supabase_client else None

def get_project_id(project_name: str) -> str:
    """统一的项目 ID 生成逻辑 (MD5 12位)"""
    return hashlib.md5(project_name.encode()).hexdigest()[:12]

def db_get_projects(limit: int = 50):
    client = get_supabase_client()
    if not client: return []
    try:
        result = client.table("projects").select("project_name, creation_time, status, current_step, tags, model_name, brief").order("creation_time", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        logger.error(f"数据库查询失败: {e}")
        return []

def db_get_project(project_name: str):
    client = get_supabase_client()
    if not client: return None
    try:
        result = client.table("projects").select("*").eq("project_name", project_name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"数据库查询失败: {e}")
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
        logger.error(f"数据库插入失败: {e}")
        return None

def db_update_project(project_name: str, **kwargs):
    client = get_supabase_client()
    if not client: return None
    try:
        result = client.table("projects").update(kwargs).eq("project_name", project_name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"数据库更新失败: {e}")
        return None

def save_project_content(project_name: str, content: Dict[str, Any]):
    """更新项目文档内容"""
    return db_update_project(project_name, content=content)

def save_project_images(project_name: str, images: List[str]):
    """更新项目图片列表"""
    return db_update_project(project_name, images=images)
