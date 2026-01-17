
import os
import time
import json
import zipfile
import io
import shutil
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src import md_parser
from src import config
from src.main import DesignWorkflow
from src.llm_wrapper import LLMService

# Initialize FastAPI app
app = FastAPI(title="AI Design Workflow API")

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
    status: str = "pending" # pending, in_progress, completed, failed
    current_step: str = ""
    tags: List[str] = []

class ProjectCreate(BaseModel):
    project_name: str
    brief: str
    model_name: str = "models/gemini-2.5-flash" # Default to working model

class StepRequest(BaseModel):
    project_name: str
    step: str # market_analysis, visual_research, design_generation, image_generation, full_report
    brief: str
    model_name: str
    context: Optional[Dict[str, Any]] = {} # Previous steps output

class AutocompleteRequest(BaseModel):
    brief: str
    model_name: str = "models/gemma-3-12b-it"

class TagsRequest(BaseModel):
    brief: str
    model_name: str = "models/gemini-2.5-flash-lite"

# Helper to manage metadata
def get_metadata(project_dir: str) -> Optional[ProjectMetadata]:
    meta_path = os.path.join(project_dir, "project_info.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ProjectMetadata(**data)
        except:
            pass
    return None

def save_metadata(project_dir: str, metadata: ProjectMetadata):
    meta_path = os.path.join(project_dir, "project_info.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata.dict(), f, indent=4, ensure_ascii=False)

# Helper to get workflow instance
def get_workflow(project_name: str, model_name: str):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(os.path.dirname(root_dir), "projects", project_name)
    
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
        # Initialize metadata for new project
        meta = ProjectMetadata(
            project_name=project_name,
            brief="", # Will be updated by first step
            model_name=model_name,
            creation_time=time.time(),
            status="pending"
        )
        save_metadata(project_dir, meta)
        
    config_path = os.path.join(os.path.dirname(root_dir), "CONFIG.md")
    custom_config = {
        'OPENAI_API_KEY': config.OPENAI_API_KEY,
        'OPENAI_BASE_URL': config.OPENAI_BASE_URL,
        'DEFAULT_MODEL': model_name,
        'prompts': md_parser.parse_config_md(config_path).get('prompts', {}) if os.path.exists(config_path) else {}
    }
    
    return DesignWorkflow(output_dir=project_dir, custom_config=custom_config), project_dir

# Endpoints

@app.get("/api/projects")
def list_projects():
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
                projects.append({
                    "project_name": d,
                    "brief": "",
                    "model_name": "",
                    "creation_time": os.path.getmtime(path),
                    "status": "completed",
                    "tags": []
                })
    
    # Sort by creation time desc
    projects.sort(key=lambda x: x["creation_time"], reverse=True)
    return projects

@app.get("/api/project/{project_name}")
def get_project(project_name: str):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_dir = os.path.join(root_dir, "projects", project_name)
    
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")
        
    meta = get_metadata(project_dir)
    
    def read_file(fname):
        path = os.path.join(project_dir, fname)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    # Scan images
    images = []
    for f in os.listdir(project_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            images.append(f"/projects/{project_name}/{f}")
            
    # Sort images by time (simulated by checking file mtime)
    images.sort(key=lambda x: os.path.getmtime(os.path.join(project_dir, os.path.basename(x))), reverse=True)

    return {
        "metadata": meta.dict() if meta else {
            "project_name": project_name,
            "brief": "",
            "creation_time": os.path.getmtime(project_dir),
            "status": "completed",
            "tags": []
        },
        "market_analysis": read_file("1_Market_Analysis.md"),
        "visual_research": read_file("2_Visual_Research.md"),
        "design_proposals": read_file("3_Design_Proposals.md"),
        "full_report": read_file("Full_Design_Report.md"),
        "images": images
    }

@app.post("/api/workflow/step")
def run_step(req: StepRequest):
    workflow, project_dir = get_workflow(req.project_name, req.model_name)
    
    # Update metadata status
    meta = get_metadata(project_dir)
    if meta:
        meta.status = "in_progress"
        meta.current_step = req.step
        meta.brief = req.brief # Update brief
        save_metadata(project_dir, meta)

    result = ""
    prompts = []
    
    try:
        # Determine model based on step to enforce "Best Model for Task" strategy
        step_model = req.model_name
        
        # Enforce model mapping based on task type
        if req.step in ["market_analysis", "visual_research"]:
            # Research tasks: gemini-2.5-flash
            step_model = "models/gemini-2.5-flash"
        elif req.step == "design_generation":
            # Prompt/Design tasks: gemini-3-flash
            step_model = "models/gemini-3-flash-preview"

        if req.step == "market_analysis":
            result, _ = workflow.step_market_analysis(req.brief, model=step_model)
            workflow._save_intermediate("1_Market_Analysis.md", result)
            
        elif req.step == "visual_research":
            market_analysis = req.context.get("market_analysis", "")
            result, _ = workflow.step_visual_research(req.brief, market_analysis, model=step_model)
            workflow._save_intermediate("2_Visual_Research.md", result)
            
        elif req.step == "design_generation":
            market_analysis = req.context.get("market_analysis", "")
            visual_research = req.context.get("visual_research", "")
            result, prompts = workflow.step_design_generation(req.brief, market_analysis, visual_research, model=step_model)
            workflow._save_intermediate("3_Design_Proposals.md", result)
            
        elif req.step == "image_generation":
            prompts_list = req.context.get("design_prompts", [])
            workflow.step_image_generation(prompts_list)
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
            
        return {"status": "success", "result": result, "prompts": prompts}
        
    except Exception as e:
        if meta:
            meta.status = "failed"
            save_metadata(project_dir, meta)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/autocomplete")
def ai_autocomplete(req: AutocompleteRequest):
    try:
        llm = LLMService(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        prompt = f"""
You are an expert product manager and industrial design strategist.
Please expand the following short user brief into a detailed, professional design requirement document.
Include target audience, aesthetic preferences (CMF), functional requirements, and market positioning.
Keep it concise but comprehensive (around 200-300 words).

User Brief: "{req.brief}"

Expanded Requirements:
"""
        messages = [{"role": "user", "content": prompt}]
        expanded_brief = llm.chat_completion(messages, model=req.model_name)
        return {"expanded_brief": expanded_brief.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/tags")
def ai_tags(req: TagsRequest):
    try:
        llm = LLMService(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        prompt = f"""
Analyze the following design brief and extract 3-6 relevant style or category tags.
Return ONLY a JSON array of strings, e.g. ["#Minimalist", "#SmartHome", "#EcoFriendly"].

Brief: "{req.brief}"
"""
        messages = [{"role": "user", "content": prompt}]
        response = llm.chat_completion(messages, model=req.model_name)
        
        # Clean up response to ensure it's valid JSON
        response = response.replace("```json", "").replace("```", "").strip()
        try:
            tags = json.loads(response)
        except:
            # Fallback if LLM doesn't return valid JSON
            tags = [t.strip() for t in response.split(',')]
            
        return {"tags": tags}
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
                if file == "project_info.json": continue # Skip internal metadata if desired, but keeping it is fine too
                
                file_path = os.path.join(root, file)
                # Calculate path relative to project_dir
                rel_path = os.path.relpath(file_path, project_dir)
                zf.write(file_path, arcname=rel_path)
    
    mem_zip.seek(0)
    
    return StreamingResponse(
        mem_zip, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={project_name}.zip"}
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
