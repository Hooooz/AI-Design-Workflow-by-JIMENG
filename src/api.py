import os
import sys
import time
import json
import zipfile
import io
import shutil

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import md_parser
import config
from main import DesignWorkflow
from llm_wrapper import LLMService
from task_manager import TaskRegistry, compute_dedup_key, normalize_text

# Initialize Supabase database connection
_supabase_client = None


def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                from supabase import create_client

                _supabase_client = create_client(
                    config.SUPABASE_URL, config.SUPABASE_KEY
                )
            except ImportError:
                print("supabase-py 未安装，数据库功能不可用")
                _supabase_client = False
            except Exception as e:
                print(f"Supabase 连接失败: {e}")
                _supabase_client = False
    return _supabase_client if _supabase_client else None


# Database operations
def db_get_projects():
    client = get_supabase_client()
    if not client:
        return []
    try:
        result = (
            client.table("projects")
            .select("*")
            .order("creation_time", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []


def db_get_project(project_name: str):
    client = get_supabase_client()
    if not client:
        return None
    try:
        result = (
            client.table("projects")
            .select("*")
            .eq("project_name", project_name)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return None


def db_create_project(
    project_name: str, brief: str, model_name: str, tags: List[str] = None
):
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = {
            "project_name": project_name,
            "brief": brief,
            "model_name": model_name,
            "creation_time": time.time(),
            "status": "pending",
            "current_step": "",
            "tags": tags or [],
            "content": {},  # 文档内容 JSON
        }
        result = client.table("projects").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"数据库插入失败: {e}")
        return None


def db_update_project(project_name: str, **kwargs):
    client = get_supabase_client()
    if not client:
        return None
    try:
        result = (
            client.table("projects")
            .update(kwargs)
            .eq("project_name", project_name)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"数据库更新失败: {e}")
        return None


def db_delete_project(project_name: str):
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("projects").delete().eq("project_name", project_name).execute()
        return True
    except Exception as e:
        print(f"数据库删除失败: {e}")
        return False
    try:
        client.table("projects").delete().eq("project_name", project_name).execute()
        return True
    except Exception as e:
        print(f"数据库删除失败: {e}")
        return False


# Initialize FastAPI app
app = FastAPI(title="AI Design Workflow API")

task_registry = TaskRegistry()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define models
class ProjectMetadata(BaseModel):
    project_name: str
    brief: str
    model_name: str
    creation_time: float
    status: str = "pending"  # pending, in_progress, completed, failed
    current_step: str = ""
    tags: List[str] = []


class ProjectCreate(BaseModel):
    project_name: str
    brief: str
    model_name: str = "gemini-2.0-flash-exp"


class StepRequest(BaseModel):
    project_name: str
    step: str  # market_analysis, visual_research, design_generation, image_generation, full_report
    brief: str
    model_name: str
    context: Optional[Dict[str, Any]] = {}  # Previous steps output
    settings: Optional[
        Dict[str, Any]
    ] = {}  # User settings like image_count, persona, etc.


class GenerateMoreRequest(BaseModel):
    project_name: str
    count: int = 4
    model_name: str = "gemini-2.5-flash-lite"
    settings: Optional[Dict[str, Any]] = {}


class AutocompleteRequest(BaseModel):
    brief: str
    model_name: str = "gemini-2.5-flash-lite"


class TagsRequest(BaseModel):
    brief: str
    model_name: str = "gemini-2.5-flash-lite"


# Helper to manage metadata
def get_metadata(project_dir: str) -> Optional[ProjectMetadata]:
    meta_path = os.path.join(project_dir, "project_info.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProjectMetadata(**data)
        except:
            pass
    return None


def save_metadata(project_dir: str, metadata: ProjectMetadata):
    meta_path = os.path.join(project_dir, "project_info.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata.dict(), f, indent=4, ensure_ascii=False)

    # 同步到数据库
    try:
        db_update_project(
            metadata.project_name,
            brief=metadata.brief,
            status=metadata.status,
            current_step=metadata.current_step,
            tags=metadata.tags,
            model_name=metadata.model_name,
        )
    except Exception as e:
        print(f"数据库同步失败: {e}")


def save_project_content(project_name: str, content: Dict[str, str]):
    """保存项目文档内容到数据库"""
    try:
        db_update_project(project_name, content=content)
    except Exception as e:
        print(f"保存项目内容失败: {e}")


def save_intermediate_and_db(workflow, project_name: str, filename: str, content: str):
    """保存中间文件到文件系统和数据库"""
    # 保存到文件系统
    workflow._save_intermediate(filename, content)

    # 映射文件名到数据库字段
    content_mapping = {
        "1_Market_Analysis.md": "market_analysis",
        "2_Visual_Research.md": "visual_research",
        "3_Design_Proposals.md": "design_proposals",
        "Full_Design_Report.md": "full_report",
    }

    field = content_mapping.get(filename)
    if field:
        # 获取现有数据库内容
        db_proj = db_get_project(project_name)
        existing_content = db_proj.get("content", {}) if db_proj else {}
        existing_content[field] = content

        # 保存到数据库
        save_project_content(project_name, existing_content)


# Helper to get workflow instance
def get_workflow(project_name: str, model_name: str):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(os.path.dirname(root_dir), "projects", project_name)

    is_new_project = False
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
        is_new_project = True
        # Initialize metadata for new project
        meta = ProjectMetadata(
            project_name=project_name,
            brief="",  # Will be updated by first step
            model_name=model_name,
            creation_time=time.time(),
            status="pending",
        )
        save_metadata(project_dir, meta)
        # 同时写入数据库
        db_create_project(project_name, "", model_name, [])

    config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
    md_config = (
        md_parser.parse_config_md(config_path) if os.path.exists(config_path) else {}
    )

    # 优先级: CONFIG.md > 环境变量 > config.py 默认值
    api_key = md_config.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
    base_url = md_config.get("OPENAI_BASE_URL") or config.OPENAI_BASE_URL

    custom_config = {
        "OPENAI_API_KEY": api_key,
        "OPENAI_BASE_URL": base_url,
        "DEFAULT_MODEL": model_name,
        "prompts": md_config.get("prompts", {}),
    }

    return DesignWorkflow(
        output_dir=project_dir, custom_config=custom_config
    ), project_dir


# Endpoints


@app.get("/api/health")
def health_check():
    """
    健康检查接口，用于验证服务状态及 LLM 配置
    """
    status = {
        "status": "ok",
        "timestamp": time.time(),
        "env": config.ENV,
        "llm_configured": bool(config.OPENAI_API_KEY),
        "base_url": config.OPENAI_BASE_URL,
    }

    # 简单的连通性测试 (可选)
    # try:
    #     llm = LLMService()
    #     if llm.client:
    #         status["llm_connection"] = "connected"
    # except Exception as e:
    #     status["llm_connection"] = f"error: {str(e)}"

    return status


@app.get("/api/projects")
def list_projects():
    # 优先从数据库获取
    db_projects = db_get_projects()
    if db_projects:
        return db_projects

    # Fallback: 从文件系统获取
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_dir = os.path.join(root_dir, "projects")

    if not os.path.exists(projects_dir):
        return []

    projects = []
    for d in os.listdir(projects_dir):
        path = os.path.join(projects_dir, d)
        if os.path.isdir(path):
            meta = get_metadata(path)
            if meta:
                projects.append(meta.dict())
            else:
                # Fallback for old projects
                projects.append(
                    {
                        "project_name": d,
                        "brief": "",
                        "model_name": "",
                        "creation_time": os.path.getmtime(path),
                        "status": "completed",
                        "tags": [],
                    }
                )

    # Sort by creation time desc
    projects.sort(key=lambda x: x["creation_time"], reverse=True)
    return projects


@app.get("/api/project/{project_name}")
def get_project(project_name: str):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_dir = os.path.join(root_dir, "projects", project_name)

    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")

    # 优先从数据库获取元数据
    db_meta = db_get_project(project_name)

    meta = get_metadata(project_dir)

    def read_file(fname):
        base_name = os.path.splitext(fname)[0]
        md_path = os.path.join(project_dir, fname)

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()

        json_path = os.path.join(project_dir, f"{base_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "content" in data:
                            return data["content"]
                        if "summary" in data and "content" not in data:
                            return data.get("summary", "")
                        if "markdown" in data:
                            return data["markdown"]
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except:
                pass

        return ""

    # Scan images
    images = []
    for f in os.listdir(project_dir):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            images.append(f"/projects/{project_name}/{f}")

    # Sort images by time (simulated by checking file mtime)
    images.sort(
        key=lambda x: os.path.getmtime(os.path.join(project_dir, os.path.basename(x))),
        reverse=True,
    )

    # 优先使用数据库元数据，否则使用文件系统
    metadata = (
        db_meta
        if db_meta
        else (
            meta.dict()
            if meta
            else {
                "project_name": project_name,
                "brief": "",
                "creation_time": os.path.getmtime(project_dir),
                "status": "completed",
                "tags": [],
            }
        )
    )

    # 从数据库读取文档内容
    db_content = db_meta.get("content", {}) if db_meta else {}

    # 优先使用数据库内容，其次使用文件系统
    market_analysis = db_content.get("market_analysis", "") or read_file(
        "1_Market_Analysis.md"
    )
    visual_research = db_content.get("visual_research", "") or read_file(
        "2_Visual_Research.md"
    )
    design_proposals = db_content.get("design_proposals", "") or read_file(
        "3_Design_Proposals.md"
    )
    full_report = db_content.get("full_report", "") or read_file(
        "Full_Design_Report.md"
    )

    return {
        "metadata": metadata,
        "market_analysis": market_analysis,
        "visual_research": visual_research,
        "design_proposals": design_proposals,
        "full_report": full_report,
        "images": images,
    }


class RunAllRequest(BaseModel):
    project_name: str
    brief: str
    model_name: str = "gemini-2.5-flash-lite"
    settings: Optional[Dict[str, Any]] = {}


def background_run_all(
    project_name: str, brief: str, model_name: str, settings: Dict[str, Any]
):
    """
    后台执行全流程任务
    """
    print(f"🔄 [Background] Starting full workflow for: {project_name}")
    workflow, project_dir = get_workflow(project_name, model_name)

    # 1. Update status to in_progress
    meta = get_metadata(project_dir)
    if meta:
        meta.status = "in_progress"
        meta.current_step = "market_analysis"
        meta.brief = brief
        save_metadata(project_dir, meta)

    try:
        # Step 1: Market Analysis
        meta.current_step = "market_analysis"
        save_metadata(project_dir, meta)
        market_analysis, _ = workflow.step_market_analysis(brief)
        save_intermediate_and_db(
            workflow, project_name, "1_Market_Analysis.md", market_analysis
        )

        # Step 2: Visual Research
        meta.current_step = "visual_research"
        save_metadata(project_dir, meta)
        visual_research, _ = workflow.step_visual_research(brief, market_analysis)
        save_intermediate_and_db(
            workflow, project_name, "2_Visual_Research.md", visual_research
        )

        # Step 3: Design Generation
        meta.current_step = "design_generation"
        save_metadata(project_dir, meta)
        image_count = settings.get("image_count", 4)
        persona = settings.get("persona", "")
        design_proposals, prompts = workflow.step_design_generation(
            brief,
            market_analysis,
            visual_research,
            image_count=image_count,
            persona=persona,
        )
        save_intermediate_and_db(
            workflow, project_name, "3_Design_Proposals.md", design_proposals
        )

        # Step 4: Image Generation
        meta.current_step = "image_generation"
        save_metadata(project_dir, meta)
        jimeng_session_id = settings.get("jimeng_session_id")
        workflow.step_image_generation(prompts, session_id=jimeng_session_id)

        # Step 5: Full Report
        meta.current_step = "full_report"
        save_metadata(project_dir, meta)
        workflow._save_report(brief, market_analysis, visual_research, design_proposals)

        # Finish
        meta.status = "completed"
        meta.current_step = ""
        save_metadata(project_dir, meta)
        print(f"✅ [Background] Full workflow completed for: {project_name}")

    except Exception as e:
        print(f"❌ [Background] Workflow failed: {e}")
        meta.status = "failed"
        save_metadata(project_dir, meta)


@app.post("/api/workflow/run_all")
def run_all_workflow(req: RunAllRequest, background_tasks: BackgroundTasks):
    """
    异步启动全流程任务
    """
    workflow, project_dir = get_workflow(req.project_name, req.model_name)

    # Initialize metadata if not exists
    if not get_metadata(project_dir):
        # Create folder and meta
        pass  # get_workflow already does this

    # Add to background tasks
    background_tasks.add_task(
        background_run_all, req.project_name, req.brief, req.model_name, req.settings
    )

    return {"status": "accepted", "message": "Workflow started in background"}


@app.post("/api/workflow/step")
def run_step(req: StepRequest):
    brief_norm = normalize_text(req.brief)
    dedup_key = compute_dedup_key(
        f"workflow_step:{req.step}",
        {
            "project_name": req.project_name,
            "step": req.step,
            "brief": brief_norm,
            "model_name": req.model_name,
            "context": req.context or {},
            "settings": req.settings or {},
        },
    )
    entry, created = task_registry.get_or_create(f"workflow_step:{req.step}", dedup_key)
    if not created:
        waited = task_registry.wait(entry.task_id, timeout_s=900)
        if not waited:
            raise HTTPException(status_code=500, detail="Task not found")
        if waited.status == "completed":
            payload = waited.result or {}
            return {
                "status": "success",
                "result": payload.get("result", ""),
                "prompts": payload.get("prompts", []),
                "cached": True,
                "duration_ms": waited.duration_ms or 0,
            }
        if waited.status == "failed":
            raise HTTPException(
                status_code=500, detail=waited.error_message or "Task failed"
            )
        raise HTTPException(status_code=504, detail="Task timeout")

    workflow, project_dir = get_workflow(req.project_name, req.model_name)

    # Update metadata status
    meta = get_metadata(project_dir)
    if meta:
        meta.status = "in_progress"
        meta.current_step = req.step
        meta.brief = req.brief  # Update brief
        save_metadata(project_dir, meta)

    result = ""
    prompts = []

    try:
        start_time = time.time()
        if req.step == "market_analysis":
            result, _ = workflow.step_market_analysis(req.brief)
            save_intermediate_and_db(
                workflow, req.project_name, "1_Market_Analysis.md", result
            )

        elif req.step == "visual_research":
            market_analysis = req.context.get("market_analysis", "")
            result, _ = workflow.step_visual_research(req.brief, market_analysis)
            save_intermediate_and_db(
                workflow, req.project_name, "2_Visual_Research.md", result
            )

        elif req.step == "design_generation":
            market_analysis = req.context.get("market_analysis", "")
            visual_research = req.context.get("visual_research", "")

            image_count = req.settings.get("image_count", 4)
            persona = req.settings.get("persona", "")

            result, prompts = workflow.step_design_generation(
                req.brief,
                market_analysis,
                visual_research,
                image_count=image_count,
                persona=persona,
            )
            save_intermediate_and_db(
                workflow, req.project_name, "3_Design_Proposals.md", result
            )

        elif req.step == "image_generation":
            prompts_list = req.context.get("design_prompts", [])
            jimeng_session_id = req.settings.get("jimeng_session_id")
            workflow.step_image_generation(prompts_list, session_id=jimeng_session_id)
            result = "Images generated"

        elif req.step == "full_report":
            ma = req.context.get("market_analysis", "")
            vr = req.context.get("visual_research", "")
            dp = req.context.get("design_proposals", "")
            path = workflow._save_report(req.brief, ma, vr, dp)
            result = f"Report saved to {path}"

        # Update metadata to completed if it's the last step or just update current state
        if meta:
            if req.step == "full_report":
                meta.status = "completed"
            meta.current_step = ""
            save_metadata(project_dir, meta)

        duration_ms = int((time.time() - start_time) * 1000)
        task_registry.complete(
            entry.task_id,
            result={"result": result, "prompts": prompts},
            duration_ms=duration_ms,
        )
        return {
            "status": "success",
            "result": result,
            "prompts": prompts,
            "cached": False,
            "duration_ms": duration_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        if meta:
            meta.status = "failed"
            save_metadata(project_dir, meta)
        if "entry" in locals():
            task_registry.fail(entry.task_id, error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/step/stream")
def run_step_stream(req: StepRequest):
    """
    流式运行工作流步骤
    """
    workflow, project_dir = get_workflow(req.project_name, req.model_name)

    # Update metadata status
    meta = get_metadata(project_dir)
    if meta:
        meta.status = "in_progress"
        meta.current_step = req.step
        meta.brief = req.brief  # Update brief
        save_metadata(project_dir, meta)

    async def stream_generator():
        try:
            if req.step == "market_analysis":
                stream_response = workflow.step_market_analysis(req.brief, stream=True)
                full_content = ""
                for chunk in stream_response:
                    full_content += chunk
                    yield chunk
                save_intermediate_and_db(
                    workflow, req.project_name, "1_Market_Analysis.md", full_content
                )

            elif req.step == "visual_research":
                market_analysis = req.context.get("market_analysis", "")
                stream_response = workflow.step_visual_research(
                    req.brief, market_analysis, stream=True
                )
                full_content = ""
                for chunk in stream_response:
                    full_content += chunk
                    yield chunk
                save_intermediate_and_db(
                    workflow, req.project_name, "2_Visual_Research.md", full_content
                )

            elif req.step == "design_generation":
                market_analysis = req.context.get("market_analysis", "")
                visual_research = req.context.get("visual_research", "")
                image_count = req.settings.get("image_count", 4)
                persona = req.settings.get("persona", "")

                stream_response = workflow.step_design_generation(
                    req.brief,
                    market_analysis,
                    visual_research,
                    image_count=image_count,
                    persona=persona,
                    stream=True,
                )
                full_content = ""
                for chunk in stream_response:
                    full_content += chunk
                    yield chunk
                save_intermediate_and_db(
                    workflow, req.project_name, "3_Design_Proposals.md", full_content
                )

            # Update metadata to completed if needed
            # 这里简化处理，实际应该在流式结束后更新
            # 由于是 generator，这里执行不到，需要放在循环外或者 finally 块

        except Exception as e:
            yield f"\n\nError: {str(e)}"
            if meta:
                meta.status = "failed"
                save_metadata(project_dir, meta)

    return StreamingResponse(stream_generator(), media_type="text/plain")


@app.post("/api/ai/autocomplete/stream")
def ai_autocomplete_stream(req: AutocompleteRequest):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
    md_config = (
        md_parser.parse_config_md(config_path) if os.path.exists(config_path) else {}
    )
    api_key = md_config.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
    base_url = md_config.get("OPENAI_BASE_URL") or config.OPENAI_BASE_URL

    llm = LLMService(api_key=api_key, base_url=base_url)

    # Load prompt from CONFIG.md
    default_prompt = """
You are an expert product manager and industrial design strategist.
Please expand the following short user brief into a detailed, professional design requirement document.
Include target audience, aesthetic preferences (CMF), functional requirements, and market positioning.
Keep it concise but comprehensive (around 200-300 words).

User Brief: "{brief}"

Expanded Requirements:
"""
    prompts = md_config.get("prompts", {})
    prompt_template = prompts.get("autocomplete", default_prompt)
    prompt = prompt_template.format(brief=req.brief)

    messages = [{"role": "user", "content": prompt}]

    return StreamingResponse(
        llm.chat_completion_stream(messages, model=req.model_name),
        media_type="text/plain",
    )


@app.post("/api/ai/autocomplete")
def ai_autocomplete(req: AutocompleteRequest):
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
        md_config = (
            md_parser.parse_config_md(config_path)
            if os.path.exists(config_path)
            else {}
        )
        api_key = md_config.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
        base_url = md_config.get("OPENAI_BASE_URL") or config.OPENAI_BASE_URL

        brief_norm = normalize_text(req.brief)
        dedup_key = compute_dedup_key(
            "autocomplete", {"brief": brief_norm, "model_name": req.model_name}
        )
        entry, created = task_registry.get_or_create("autocomplete", dedup_key)

        if not created:
            waited = task_registry.wait(entry.task_id, timeout_s=240)
            if not waited:
                raise HTTPException(status_code=500, detail="Task not found")
            if waited.status == "completed":
                return {
                    "expanded_brief": waited.result or "",
                    "cached": True,
                    "duration_ms": waited.duration_ms or 0,
                }
            if waited.status == "failed":
                raise HTTPException(
                    status_code=500, detail=waited.error_message or "Task failed"
                )
            raise HTTPException(status_code=504, detail="Task timeout")

        start_time = time.time()

        llm = LLMService(api_key=api_key, base_url=base_url)

        # Load prompt from CONFIG.md
        default_prompt = """
You are an expert product manager and industrial design strategist.
Please expand the following short user brief into a detailed, professional design requirement document.
Include target audience, aesthetic preferences (CMF), functional requirements, and market positioning.
Keep it concise but comprehensive (around 200-300 words).

User Brief: "{brief}"

Expanded Requirements:
"""
        prompts = md_config.get("prompts", {})
        prompt_template = prompts.get("autocomplete", default_prompt)
        prompt = prompt_template.format(brief=req.brief)

        messages = [{"role": "user", "content": prompt}]
        expanded_brief = llm.chat_completion(messages, model=req.model_name)

        duration_ms = int((time.time() - start_time) * 1000)
        result = expanded_brief.strip()
        task_registry.complete(entry.task_id, result=result, duration_ms=duration_ms)
        return {"expanded_brief": result, "cached": False, "duration_ms": duration_ms}
    except HTTPException:
        raise
    except Exception as e:
        if "entry" in locals():
            task_registry.fail(entry.task_id, error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/tags")
def ai_tags(req: TagsRequest):
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
        md_config = (
            md_parser.parse_config_md(config_path)
            if os.path.exists(config_path)
            else {}
        )
        api_key = md_config.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
        base_url = md_config.get("OPENAI_BASE_URL") or config.OPENAI_BASE_URL

        brief_norm = normalize_text(req.brief)
        dedup_key = compute_dedup_key(
            "tags", {"brief": brief_norm, "model_name": req.model_name}
        )
        entry, created = task_registry.get_or_create("tags", dedup_key)

        if not created:
            waited = task_registry.wait(entry.task_id, timeout_s=60)
            if not waited:
                raise HTTPException(status_code=500, detail="Task not found")
            if waited.status == "completed":
                return {
                    "tags": waited.result or [],
                    "cached": True,
                    "duration_ms": waited.duration_ms or 0,
                }
            if waited.status == "failed":
                raise HTTPException(
                    status_code=500, detail=waited.error_message or "Task failed"
                )
            raise HTTPException(status_code=504, detail="Task timeout")

        start_time = time.time()

        llm = LLMService(api_key=api_key, base_url=base_url)

        # Load prompt from CONFIG.md via md_parser
        default_prompt = """
Analyze the following design brief and extract 3-6 relevant style or category tags.
Return ONLY a JSON array of strings, e.g. ["#Minimalist", "#SmartHome", "#EcoFriendly"].

Brief: "{brief}"
"""
        prompts = md_config.get("prompts", {})
        prompt_template = prompts.get("tags", default_prompt)
        prompt = prompt_template.format(brief=req.brief)

        messages = [{"role": "user", "content": prompt}]
        response = llm.chat_completion(messages, model=req.model_name)

        # Clean up response to ensure it's valid JSON
        response = response.replace("```json", "").replace("```", "").strip()
        try:
            tags = json.loads(response)
        except:
            # Fallback if LLM doesn't return valid JSON
            tags = [t.strip() for t in response.split(",")]

        duration_ms = int((time.time() - start_time) * 1000)
        task_registry.complete(entry.task_id, result=tags, duration_ms=duration_ms)
        return {"tags": tags, "cached": False, "duration_ms": duration_ms}
    except HTTPException:
        raise
    except Exception as e:
        if "entry" in locals():
            task_registry.fail(entry.task_id, error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/generate-images")
def generate_more_images(req: GenerateMoreRequest):
    workflow, project_dir = get_workflow(req.project_name, req.model_name)

    # Check if project exists and has design proposals
    meta = get_metadata(project_dir)
    if not meta:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load design proposals to use as context
    design_proposals_path = os.path.join(project_dir, "3_Design_Proposals.md")
    if not os.path.exists(design_proposals_path):
        raise HTTPException(
            status_code=400, detail="Must complete design generation first"
        )

    with open(design_proposals_path, "r", encoding="utf-8") as f:
        design_proposals = f.read()

    # Create a prompt to generate variations
    persona = req.settings.get("persona", "")
    persona_instruction = f"以【{persona}】的视角，" if persona else ""

    # Load prompt from CONFIG.md
    # We need to load config first since this endpoint doesn't do it yet
    root_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
    md_config = (
        md_parser.parse_config_md(config_path) if os.path.exists(config_path) else {}
    )
    prompts_cfg = md_config.get("prompts", {})

    default_prompt = """
    基于以下设计方案：
    {design_proposals}
    
    请{persona_instruction}再构思 {count} 个新的、有差异化的设计方案变体，并提供对应的绘图 Prompt。
    请只输出 JSON 格式，包含 `prompts` 列表。
    """

    prompt_template = prompts_cfg.get("variant_generator", default_prompt)

    # Handle design proposals length limit for prompt
    dp_content = (
        design_proposals[:3000] + "..."
        if len(design_proposals) > 3000
        else design_proposals
    )

    prompt = prompt_template.format(
        design_proposals=dp_content,
        persona_instruction=persona_instruction,
        count=req.count,
    )

    try:
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        response = workflow.llm.chat_completion(messages)

        # Parse and Generate
        _, prompts = workflow._process_llm_json_response(response)

        jimeng_session_id = req.settings.get("jimeng_session_id")
        workflow.step_image_generation(
            prompts, session_id=jimeng_session_id, skip_json_update=True
        )

        return {"status": "success", "count": len(prompts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/project/{project_name}/export")
def export_project(project_name: str):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_dir = os.path.join(root_dir, "projects", project_name)

    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")

    # Create a memory zip
    mem_zip = io.BytesIO()

    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file == "project_info.json":
                    continue  # Skip internal metadata if desired, but keeping it is fine too

                file_path = os.path.join(root, file)
                # Calculate path relative to project_dir
                rel_path = os.path.relpath(file_path, project_dir)
                zf.write(file_path, arcname=rel_path)

    mem_zip.seek(0)

    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_name}.zip"},
    )


# Mount projects directory as static files
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
projects_dir = os.path.join(root_dir, "projects")
if not os.path.exists(projects_dir):
    os.makedirs(projects_dir)

app.mount("/projects", StaticFiles(directory=projects_dir), name="projects")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
