"""
项目API路由 - AI 设计工作流 v2
"""

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..services.database import db_service, DatabaseError
from ..services.task_service import task_service
from ..api.response import success_response, error_response, NotFoundError
from ..core.logger import logger


router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/health")
async def health_check():
    """健康检查"""
    return success_response(
        {
            "status": "healthy",
            "storage": "supabase",
            "timestamp": logger.info("Health check") or "",
        }
    )


@router.get("/projects")
async def list_projects(limit: int = 50):
    """获取项目列表"""
    try:
        projects = db_service.get_projects(limit=limit)
        return success_response(projects)
    except DatabaseError as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/project/create")
async def create_project(
    project_name: str,
    brief: str,
    model_name: str = "gemini-2.5-flash",
):
    """创建项目"""
    existing = db_service.get_project(project_name)
    if existing:
        return success_response(existing)

    try:
        project = db_service.create_project(
            project_name=project_name,
            brief=brief,
            model_name=model_name,
        )
        return success_response(project)
    except DatabaseError as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_name}")
async def get_project(project_name: str):
    """获取项目详情"""
    project = db_service.get_project(project_name)
    if not project:
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_name}"
        )

    return success_response(project)


@router.post("/project/{project_name}/update")
async def update_project(
    project_name: str,
    **kwargs,
):
    """更新项目"""
    project = db_service.update_project(project_name, **kwargs)
    if not project:
        raise HTTPException(
            status_code=404, detail=f"Project not found: {project_name}"
        )

    return success_response(project)
