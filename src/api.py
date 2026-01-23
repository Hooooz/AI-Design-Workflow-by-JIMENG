import os
import sys
import time
import json
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import logger
from services.project_service import ProjectService
from services import db_service
from main import DesignWorkflow
from task_manager import TaskRegistry, compute_dedup_key
from core.config_manager import config_manager
from llm_wrapper import LLMService
import config

app = FastAPI(title="AI Design Workflow API (Cloud Only)")
task_registry = TaskRegistry()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ProjectCreate(BaseModel):
    project_name: str
    brief: str
    model_name: str = config.DEFAULT_MODEL

class StepRequest(BaseModel):
    project_name: str
    step: str
    brief: str
    model_name: str
    context: Optional[Dict[str, Any]] = {}
    settings: Optional[Dict[str, Any]] = {}

class AutocompleteRequest(BaseModel):
    brief: str
    model_name: str = config.DEFAULT_MODEL

# --- Project Management ---
@app.get("/api/health")
def health_check():
    return {"status": "ok", "storage": "supabase_only", "timestamp": time.time()}

@app.get("/api/projects")
def list_projects(limit: int = 50):
    return db_service.db_get_projects(limit=limit)

@app.post("/api/project/create")
def create_project(req: ProjectCreate):
    existing = db_service.db_get_project(req.project_name)
    if existing:
        return existing

    new_proj = db_service.db_create_project(
        project_name=req.project_name,
        brief=req.brief,
        model_name=req.model_name
    )
    if not new_proj:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return new_proj

@app.get("/api/project/{project_name}")
def get_project(project_name: str):
    project = db_service.db_get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    processed_project = ProjectService.process_project_data(project)
    return processed_project

# --- AI Assistance ---

@app.post("/api/ai/autocomplete")
def ai_autocomplete(req: AutocompleteRequest):
    llm = LLMService(api_key=config_manager.openai_api_key, base_url=config_manager.openai_base_url)
    prompt_tpl = config_manager.get_prompt("autocomplete", "请根据以下简要描述扩展为专业设计需求：\n{brief}")
    prompt = prompt_tpl.format(brief=req.brief)

    response = llm.chat_completion([{"role": "user", "content": prompt}])
    return {"expanded_brief": response.strip()}

@app.post("/api/ai/tags")
def ai_tags(req: AutocompleteRequest):
    llm = LLMService(api_key=config_manager.openai_api_key, base_url=config_manager.openai_base_url)
    prompt_tpl = config_manager.get_prompt("tags", "请为以下需求提取3-5个标签（如 #简约 #科技）：\n{brief}")
    prompt = prompt_tpl.format(brief=req.brief)

    response = llm.chat_completion([{"role": "user", "content": prompt}])
    # Clean tags
    tags = [t.strip() for t in response.replace("[", "").replace("]", "").replace('"', "").split(",") if "#" in t]
    return {"tags": tags}

# --- Workflow Execution ---

class RunAllRequest(BaseModel):
    project_name: str
    brief: str
    model_name: str = config.DEFAULT_MODEL
    image_count: int = 4
    persona: str = ""

def _run_all_background(task_id: str, req: RunAllRequest):
    """后台执行完整工作流"""
    try:
        start_time = time.time()
        # 传入用户指定的模型
        workflow = DesignWorkflow(
            project_name=req.project_name,
            custom_config={"DEFAULT_MODEL": req.model_name}
        )

        # Step 1: Market Analysis
        db_service.db_update_project(req.project_name, status="in_progress", current_step="market_analysis")
        market_result, _ = workflow.step_market_analysis(req.brief)

        # Step 2: Visual Research
        db_service.db_update_project(req.project_name, current_step="visual_research")
        visual_result, _ = workflow.step_visual_research(req.brief, market_result)

        # Step 3: Design Generation
        db_service.db_update_project(req.project_name, current_step="design_generation")
        design_result, prompts = workflow.step_design_generation(
            req.brief, market_result, visual_result,
            image_count=req.image_count, persona=req.persona
        )

        # Step 4: Image Generation
        db_service.db_update_project(req.project_name, current_step="image_generation")
        workflow.step_image_generation(prompts)

        # Mark as completed
        db_service.db_update_project(req.project_name, status="completed", current_step="")

        duration_ms = int((time.time() - start_time) * 1000)
        task_result = {
            "status": "success",
            "project_name": req.project_name,
            "duration_ms": duration_ms,
            "steps_completed": ["market_analysis", "visual_research", "design_generation", "image_generation"]
        }
        task_registry.complete(task_id, result=task_result, duration_ms=duration_ms)
        print(f"✅ 后台任务完成: {req.project_name}")

    except Exception as e:
        print(f"❌ 后台任务失败: {e}")
        db_service.db_update_project(req.project_name, status="failed")
        task_registry.fail(task_id, str(e))

@app.post("/api/workflow/run_all")
def run_all_workflow(req: RunAllRequest, background_tasks: BackgroundTasks):
    """一键执行完整设计工作流（异步后台模式）"""
    # 1. 确保项目已创建
    existing = db_service.db_get_project(req.project_name)
    if not existing:
        db_service.db_create_project(
            project_name=req.project_name,
            brief=req.brief,
            model_name=req.model_name
        )

    # 2. 注册任务
    dedup_key = compute_dedup_key("run_all", req.dict())
    entry, created = task_registry.get_or_create("run_all", dedup_key)

    if not created:
        return {"status": "in_progress", "message": "Task already running", "task_id": entry.task_id}

    # 3. 立即更新状态为进行中
    db_service.db_update_project(req.project_name, status="in_progress", current_step="starting")

    # 4. 添加后台任务
    background_tasks.add_task(_run_all_background, entry.task_id, req)

    # 5. 立即返回
    return {
        "status": "pending",
        "message": "Workflow started in background",
        "project_name": req.project_name,
        "task_id": entry.task_id
    }

@app.post("/api/workflow/step")
def run_step(req: StepRequest):
    # 任务去重逻辑保持不变
    dedup_key = compute_dedup_key(f"step:{req.step}", req.dict())
    entry, created = task_registry.get_or_create(f"step:{req.step}", dedup_key)

    if not created:
        waited = task_registry.wait(entry.task_id, timeout_s=600)
        return waited.result if waited else {"status": "timeout"}

    try:
        start_time = time.time()
        workflow = DesignWorkflow(project_name=req.project_name)

        result = ""
        prompts = []

        # 更新项目状态
        db_service.db_update_project(req.project_name, status="in_progress", current_step=req.step)

        if req.step == "market_analysis":
            result, _ = workflow.step_market_analysis(req.brief)
        elif req.step == "visual_research":
            result, _ = workflow.step_visual_research(req.brief, req.context.get("market_analysis", ""))
        elif req.step == "design_generation":
            result, prompts = workflow.step_design_generation(
                req.brief,
                req.context.get("market_analysis", ""),
                req.context.get("visual_research", ""),
                image_count=req.settings.get("image_count", 4),
                persona=req.settings.get("persona", "")
            )
        elif req.step == "image_generation":
            workflow.step_image_generation(req.context.get("design_prompts", []))
            result = "Images generated"

        duration_ms = int((time.time() - start_time) * 1000)
        task_result = {"status": "success", "result": result, "prompts": prompts, "duration_ms": duration_ms}
        task_registry.complete(entry.task_id, result=task_result, duration_ms=duration_ms)

        return task_result
    except Exception as e:
        db_service.db_update_project(req.project_name, status="failed")
        task_registry.fail(entry.task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
