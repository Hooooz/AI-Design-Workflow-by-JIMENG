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

import config
from main import DesignWorkflow
from services import db_service
from core.config_manager import config_manager
from task_manager import TaskRegistry, compute_dedup_key, normalize_text
from llm_wrapper import LLMService

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
    model_name: str = "gemini-2.5-flash"

class StepRequest(BaseModel):
    project_name: str
    step: str
    brief: str
    model_name: str
    context: Optional[Dict[str, Any]] = {}
    settings: Optional[Dict[str, Any]] = {}

class AutocompleteRequest(BaseModel):
    brief: str
    model_name: str = "gemini-2.5-flash"

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

    # 修正图片 URL
    if "images" in project:
        project["images"] = db_service.fix_image_urls(project["images"])

    # 构造前端预期的结构：将基本信息放入 metadata
    metadata_fields = ["project_name", "brief", "model_name", "creation_time", "status", "current_step", "tags"]
    metadata = {k: project.get(k) for k in metadata_fields if k in project}

    response = {
        "metadata": metadata,
        "market_analysis": project.get("market_analysis", ""),
        "visual_research": project.get("visual_research", ""),
        "design_proposals": project.get("design_proposals", ""),
        "full_report": project.get("full_report", ""),
        "images": project.get("images", [])
    }

    return response

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
