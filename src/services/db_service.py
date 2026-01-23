import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional
from config import logger, OUTPUT_DIR

PROJECTS_ROOT = os.path.join(os.getcwd(), "projects")
os.makedirs(PROJECTS_ROOT, exist_ok=True)


def get_project_id(project_name: str) -> str:
    return hashlib.md5(project_name.encode()).hexdigest()[:12]


def _get_project_dir(project_name: str) -> str:
    return os.path.join(PROJECTS_ROOT, project_name)


def _get_project_info_path(project_name: str) -> str:
    return os.path.join(_get_project_dir(project_name), "project_info.json")


def db_get_projects(limit: int = 50):
    projects = []
    try:
        if not os.path.exists(PROJECTS_ROOT):
            return []

        for item in os.listdir(PROJECTS_ROOT):
            path = os.path.join(PROJECTS_ROOT, item)
            if os.path.isdir(path):
                info_path = os.path.join(path, "project_info.json")
                if os.path.exists(info_path):
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            projects.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error reading {info_path}: {e}")

        projects.sort(key=lambda x: x.get("creation_time", 0), reverse=True)
        return projects[:limit]
    except Exception as e:
        logger.error(f"Local DB query failed: {e}")
        return []


def db_get_project(project_name: str):
    info_path = _get_project_info_path(project_name)
    if os.path.exists(info_path):
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading project {project_name}: {e}")
    return None


def db_create_project(
    project_name: str, brief: str, model_name: str, tags: List[str] = None
):
    project_dir = _get_project_dir(project_name)
    os.makedirs(project_dir, exist_ok=True)

    data = {
        "project_name": project_name,
        "brief": brief,
        "model_name": model_name,
        "creation_time": time.time(),
        "status": "pending",
        "current_step": "",
        "tags": tags or [],
        "content": {},
        "images": [],
    }

    info_path = _get_project_info_path(project_name)
    try:
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return data
    except Exception as e:
        logger.error(f"Local DB insert failed: {e}")
        return None


def db_update_project(project_name: str, **kwargs):
    project_dir = _get_project_dir(project_name)
    if not os.path.exists(project_dir):
        return None

    info_path = _get_project_info_path(project_name)
    data = db_get_project(project_name) or {}
    data.update(kwargs)

    try:
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return data
    except Exception as e:
        logger.error(f"Local DB update failed: {e}")
        return None


def save_project_content(project_name: str, new_content: Dict[str, Any]):
    proj = db_get_project(project_name)
    if not proj:
        return None

    existing_content = proj.get("content", {})
    if not isinstance(existing_content, dict):
        existing_content = {}

    existing_content.update(new_content)
    return db_update_project(project_name, content=existing_content)


def save_project_images(project_name: str, images: List[str]):
    return db_update_project(project_name, images=images)
