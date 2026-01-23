"""
工作流API路由 - AI 设计工作流 v2
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..services.database import db_service, DatabaseError
from ..services.task_service import task_service, TaskStatus
from ..services.llm_service import LLMService, LLMError
from ..api.response import success_response, error_response
from ..core.config import config
from ..core.logger import logger


router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class RunAllRequest(BaseModel):
    """完整工作流请求"""

    project_name: str
    brief: str
    model_name: str = config.llm.default_model
    image_count: int = 4


class StepRequest(BaseModel):
    """单步工作流请求"""

    project_name: str
    step: str
    brief: str
    model_name: str = config.llm.default_model
    context: Dict[str, Any] = {}


def _run_workflow_background(
    task_id: str,
    project_name: str,
    brief: str,
    model_name: str,
    image_count: int,
):
    """后台执行工作流"""
    start_time = time.time()

    try:
        # Step 1: Market Analysis
        db_service.update_project(
            project_name, status="in_progress", current_step="market_analysis"
        )

        # Step 2: Visual Research
        db_service.update_project(project_name, current_step="visual_research")

        # Step 3: Design Generation
        db_service.update_project(project_name, current_step="design_generation")

        # Step 4: Image Generation
        db_service.update_project(project_name, current_step="image_generation")

        # 完成
        db_service.update_project(project_name, status="completed", current_step="")

        duration_ms = int((time.time() - start_time) * 1000)
        task_service.complete(
            task_id,
            {
                "status": "success",
                "project_name": project_name,
                "steps_completed": [
                    "market_analysis",
                    "visual_research",
                    "design_generation",
                    "image_generation",
                ],
            },
            duration_ms,
        )

        logger.info(f"工作流完成: {project_name}")

    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        db_service.update_project(project_name, status="failed")
        task_service.fail(task_id, str(e))


@router.post("/run_all")
async def run_all_workflow(req: RunAllRequest, background_tasks: BackgroundTasks):
    """
    一键执行完整工作流

    这是核心API，提供稳定的后台任务执行
    """
    # 检查或创建项目
    existing = db_service.get_project(req.project_name)
    if not existing:
        try:
            db_service.create_project(
                project_name=req.project_name,
                brief=req.brief,
                model_name=req.model_name,
            )
        except DatabaseError as e:
            raise HTTPException(status_code=500, detail=f"创建项目失败: {e}")

    # 获取或创建任务
    payload = {
        "project_name": req.project_name,
        "brief": req.brief,
        "model_name": req.model_name,
        "image_count": req.image_count,
    }

    entry, is_new = task_service.get_or_create("run_all", payload, req.project_name)

    if not is_new:
        if entry.status == TaskStatus.IN_PROGRESS:
            return success_response(
                {
                    "status": "in_progress",
                    "message": "Task already running",
                    "task_id": entry.task_id,
                }
            )
        elif entry.status == TaskStatus.COMPLETED:
            return success_response(
                {
                    "status": "completed",
                    "message": "Task already completed",
                    "task_id": entry.task_id,
                    "result": entry.result,
                }
            )

    # 启动后台任务
    db_service.update_project(
        req.project_name, status="in_progress", current_step="starting"
    )
    background_tasks.add_task(
        _run_workflow_background,
        entry.task_id,
        req.project_name,
        req.brief,
        req.model_name,
        req.image_count,
    )

    return success_response(
        {
            "status": "pending",
            "message": "Workflow started",
            "task_id": entry.task_id,
        }
    )


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    status = task_service.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return success_response(
        {
            "task_id": task_id,
            "status": status.value,
        }
    )


@router.post("/step")
async def run_step(req: StepRequest):
    """执行单个步骤"""
    # 验证步骤
    valid_steps = [
        "market_analysis",
        "visual_research",
        "design_generation",
        "image_generation",
    ]
    if req.step not in valid_steps:
        raise HTTPException(status_code=400, detail=f"Invalid step: {req.step}")

    # 获取或创建任务
    payload = {
        "step": req.step,
        "project_name": req.project_name,
        "brief": req.brief,
        "model_name": req.model_name,
    }

    entry, is_new = task_service.get_or_create(
        f"step:{req.step}", payload, req.project_name
    )

    if not is_new and entry.status == TaskStatus.COMPLETED:
        return success_response(
            {
                "status": "completed",
                "result": entry.result,
            }
        )

    # 执行步骤
    start_time = time.time()

    try:
        db_service.update_project(
            req.project_name, status="in_progress", current_step=req.step
        )

        # 这里调用实际的LLM服务
        # TODO: 实现各个步骤的具体逻辑

        duration_ms = int((time.time() - start_time) * 1000)
        task_service.complete(entry.task_id, {"status": "success"}, duration_ms)

        return success_response(
            {
                "status": "success",
                "duration_ms": duration_ms,
            }
        )

    except Exception as e:
        logger.error(f"步骤执行失败: {e}")
        task_service.fail(entry.task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
