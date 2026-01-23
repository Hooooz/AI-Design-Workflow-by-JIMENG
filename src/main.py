import os
import sys
import time
import re
import json
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Tuple, List

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_wrapper import LLMService
from image_gen import ImageGenService
import config
from core.config_manager import config_manager
from config import logger
from services.project_service import ProjectService

class DesignWorkflowError(Exception):
    """设计工作流基础异常类"""
    def __init__(self, message: str, step: str = None, recoverable: bool = False):
        self.message = message
        self.step = step
        self.recoverable = recoverable
        super().__init__(self.message)

class DesignWorkflow:
    def __init__(self, project_name=None, custom_config=None):
        self.project_name = project_name
        self.custom_config = custom_config or {}

        api_key = self.custom_config.get("OPENAI_API_KEY") or config_manager.openai_api_key
        base_url = self.custom_config.get("OPENAI_BASE_URL") or config_manager.openai_base_url
        self.llm = LLMService(api_key=api_key, base_url=base_url)

        jimeng_script = self.custom_config.get("JIMENG_SERVER_SCRIPT") or config.JIMENG_SERVER_SCRIPT
        self.image_gen = ImageGenService(server_script_path=jimeng_script)

        self.history = []
        self.generated_images = []
        self.output_dir = "MEMORY_ONLY"
        self.model = self.custom_config.get("DEFAULT_MODEL", config.DEFAULT_MODEL)
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        kb_path = os.path.join(root_dir, "KNOWLEDGE.md")
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                return f.read()
        return "暂无外部知识库。"

    def log(self, message):
        logger.info(message)

    def _get_prompt(self, agent_name, default_template, **kwargs):
        template = config_manager.get_prompt(agent_name, default_template)
        if "{knowledge}" in template and "knowledge" not in kwargs:
            kwargs["knowledge"] = self.knowledge_base
        try:
            return template.format(**kwargs) + "\n\n⚠️ IMPORTANT: You must output ONLY valid JSON. No conversational text. No markdown blocks. No thinking process. Start with '{' and end with '}'."
        except KeyError:
            return default_template.format(**kwargs) + "\n\n⚠️ IMPORTANT: You must output ONLY valid JSON. No conversational text. No markdown blocks. No thinking process. Start with '{' and end with '}'."

    def _process_llm_json_response(self, raw_response: str) -> Tuple[str, List[Dict], Dict]:
        # Debug logging
        logger.info(f"LLM Response parsing. Length: {len(raw_response)}")

        try:
            json_str = raw_response.strip()

            # 1. 尝试提取 Markdown 代码块 (支持 ```json 和 纯 ```)
            match = re.search(r"```(?:json)?\s*(.*?)```", raw_response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
            else:
                # 2. 尝试提取最外层的大括号内容
                # 寻找第一个 { 和最后一个 }
                start = raw_response.find('{')
                end = raw_response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = raw_response[start:end+1]

            # 3. 清理控制字符 (保留换行和制表符，避免破坏内容)
            # 移除 ASCII 0-8, 11-12, 14-31, 127
            json_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", json_str)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parse Error: {e}")
                logger.error(f"Problematic JSON (first 500 chars): {json_str[:500]}...")
                # 如果解析失败，尝试最后一种手段：如果原来的 raw_response 就是纯文本，可能根本不是 JSON
                # 这里我们抛出异常，让外层捕获
                raise e

            summary = data.get("summary", "")
            content = data.get("content", "")
            visuals = data.get("visuals", [])
            prompts = data.get("prompts", [])

            final_content = ""
            if summary: final_content += f"> 💡 **核心摘要**: {summary}\n\n"

            if visuals and self.project_name:
                self.log(f"    - 生成 {len(visuals)} 个可视化插图...")
                for item in visuals:
                    prompt = item.get("prompt", "")
                    if prompt:
                        img_url = self.image_gen.generate_image(prompt, self.output_dir, project_name=self.project_name)
                        if img_url:
                            final_content += f"\n![Concept]({img_url})\n"
                            item["image_path"] = img_url
                            self.generated_images.append(img_url)

            final_content += content
            return final_content, prompts if prompts else visuals, data
        except Exception as e:
            raise DesignWorkflowError(f"处理响应失败: {e}")

    def step_market_analysis(self, brief, stream=False):
        prompt = self._get_prompt("market_analyst", "请进行市场分析", brief=brief)
        messages = [{"role": "user", "content": prompt}]
        if stream: return self.llm.chat_completion_stream(messages)
        response = self.llm.chat_completion(messages)
        md, prompts, data = self._process_llm_json_response(response)
        return md, prompts

    def step_visual_research(self, brief, market_analysis, stream=False):
        prompt = self._get_prompt("visual_researcher", "请进行视觉调研", brief=brief, market_analysis=market_analysis)
        messages = [{"role": "user", "content": prompt}]
        if stream: return self.llm.chat_completion_stream(messages)
        response = self.llm.chat_completion(messages)
        md, prompts, data = self._process_llm_json_response(response)
        return md, prompts

    def step_design_generation(self, brief, market_analysis, visual_research, image_count=4, persona="", stream=False):
        base_prompt = self._get_prompt("product_designer", "请输出设计方案", brief=brief, market_analysis=market_analysis, visual_research=visual_research, image_count=image_count)
        full_prompt = base_prompt + (f"\n视角：{persona}\n" if persona else "")
        messages = [{"role": "user", "content": full_prompt}]
        if stream: return self.llm.chat_completion_stream(messages)
        response = self.llm.chat_completion(messages)
        md, prompts, data = self._process_llm_json_response(response)
        return json.dumps(data, ensure_ascii=False), prompts

    def step_image_generation(self, prompts_list: List[Dict], session_id=None, skip_json_update=False):
        if not prompts_list or not self.project_name: return
        valid_tasks = [(i, item.get("prompt", "")) for i, item in enumerate(prompts_list) if item.get("prompt")]

        def generate_single(p):
            return self.image_gen.generate_image(p, self.output_dir, session_id=session_id, project_name=self.project_name)

        with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_IMAGES) as executor:
            future_to_index = {executor.submit(generate_single, p): idx for idx, p in valid_tasks}
            for future in concurrent.futures.as_completed(future_to_index):
                img_url = future.result()
                if img_url:
                    prompts_list[idx := future_to_index[future]]["image_path"] = img_url
                    self.generated_images.append(img_url)

        if not skip_json_update:
            fixed_images = ProjectService.fix_image_urls(self.generated_images)
            db_service.db_update_project(self.project_name, images=fixed_images)

    def _save_intermediate(self, filename, content):
        if not self.project_name: return
        mapping = {"1_Market_Analysis.md": "market_analysis", "2_Visual_Research.md": "visual_research", "3_Design_Proposals.json": "design_proposals", "Full_Design_Report.md": "full_report"}
        field = mapping.get(filename)
        if field:
            proj = db_service.db_get_project(self.project_name)
            existing = proj.get("content", {}) if proj else {}
            existing[field] = content
            db_service.save_project_content(self.project_name, existing)

    def run(self, product_brief: str):
        self.log(f"🚀 启动 AI 设计工作流 (纯云端)，目标: {product_brief}")
        ma, _ = self.step_market_analysis(product_brief)
        self._save_intermediate("1_Market_Analysis.md", ma)
        vr, _ = self.step_visual_research(product_brief, ma)
        self._save_intermediate("2_Visual_Research.md", vr)
        dp_json, prompts = self.step_design_generation(product_brief, ma, vr)
        self._save_intermediate("3_Design_Proposals.json", dp_json)
        self.step_image_generation(prompts)
        # 更新包含图片后的设计方案
        final_dp = json.dumps({"prompts": prompts}, ensure_ascii=False, indent=2)
        self._save_intermediate("3_Design_Proposals.json", final_dp)
        self.log("📄 工作流完成，已同步至 Supabase")

def main():
    if len(sys.argv) > 1:
        brief = sys.argv[1]
        workflow = DesignWorkflow(project_name=f"manual_{int(time.time())}")
        workflow.run(brief)

if __name__ == "__main__":
    main()
