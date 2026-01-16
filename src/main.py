import os
import sys
import time
import re
import json
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Tuple, List
from llm_wrapper import LLMService
from image_gen import ImageGenService
import config
import md_parser

class DesignWorkflow:
    def __init__(self, output_dir=None, custom_config=None):
        self.custom_config = custom_config or {}
        # 优先使用 custom_config 中的 api_key
        api_key = self.custom_config.get('OPENAI_API_KEY')
        base_url = self.custom_config.get('OPENAI_BASE_URL')
        
        self.llm = LLMService(api_key=api_key, base_url=base_url)
        
        # 初始化绘图服务
        jimeng_script = self.custom_config.get('JIMENG_SERVER_SCRIPT') or config.JIMENG_SERVER_SCRIPT
        self.image_gen = ImageGenService(server_script_path=jimeng_script)
        
        self.history = []
        self.generated_images = []
        
        self.output_dir = output_dir or config.OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 加载外部知识库
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self):
        """
        加载 KNOWLEDGE.md 内容
        """
        kb_path = "KNOWLEDGE.md"
        if os.path.exists(kb_path):
            with open(kb_path, 'r', encoding='utf-8') as f:
                print(f"📚 已加载外部知识库: {kb_path}")
                return f.read()
        else:
            print("⚠️ 未找到知识库文件 KNOWLEDGE.md")
            return "暂无外部知识库。"

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run(self, product_brief: str):
        self.log(f"🚀 启动 AI 设计工作流，目标任务: {product_brief}")
        
        # Step 1: 市场与竞品分析
        self.log("🔍 Agent 1 (Market Analyst) 正在进行市场趋势分析...")
        market_analysis, _ = self.step_market_analysis(product_brief)
        self.log("✅ 市场分析完成")
        self._save_intermediate("1_Market_Analysis.md", market_analysis)

        # Step 2: 视觉参考与痛点挖掘
        self.log("🎨 Agent 2 (Visual Researcher) 正在寻找视觉参考并分析痛点...")
        visual_research, _ = self.step_visual_research(product_brief, market_analysis)
        self.log("✅ 视觉调研完成")
        self._save_intermediate("2_Visual_Research.md", visual_research)

        # Step 3: 方案生成与 Prompt 输出
        self.log("💡 Agent 3 (Product Designer) 正在构思设计方案与绘图 Prompt...")
        design_proposals, design_prompts = self.step_design_generation(product_brief, market_analysis, visual_research)
        self.log("✅ 设计方案生成完成")
        self._save_intermediate("3_Design_Proposals.md", design_proposals)

        # Step 4: 调用即梦生成图片
        self.log("🎨 Agent 4 (Image Generator) 正在根据方案生成概念图...")
        self.step_image_generation(design_prompts)
        self.log("✅ 图片生成完成")

        # Step 5: 生成报告
        report_path = self._save_report(product_brief, market_analysis, visual_research, design_proposals)
        self.log(f"📄 完整设计报告已保存至: {report_path}")

    def _get_prompt(self, agent_name, default_template, **kwargs):
        """
        获取 Prompt，优先使用 CONFIG.md 中的配置
        """
        prompts = self.custom_config.get('prompts', {})
        template = prompts.get(agent_name, default_template)
        
        # 自动注入 knowledge 参数，如果模板中有 {knowledge} 占位符
        if "{knowledge}" in template and "knowledge" not in kwargs:
            kwargs["knowledge"] = self.knowledge_base

        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.log(f"⚠️ Prompt 模板参数缺失: {e}，将使用默认模板")
            return default_template.format(**kwargs)

    def _process_llm_json_response(self, raw_response: str) -> Tuple[str, List[Dict]]:
        """
        解析 LLM 的 JSON 响应，生成插图，并返回格式化的 Markdown 和数据列表
        """
        try:
            # 尝试提取 JSON 块
            json_str = raw_response
            match = re.search(r"```json\s*(.*?)```", raw_response, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # 尝试查找第一个 { 和最后一个 }
                match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if match:
                    json_str = match.group(0)
            
            data = json.loads(json_str)
            
            summary = data.get("summary", "")
            content = data.get("content", "")
            visuals = data.get("visuals", [])
            prompts = data.get("prompts", []) # For step 3
            
            # 1. 组合 Summary
            final_content = ""
            if summary:
                final_content += f"> 💡 **核心摘要**: {summary}\n\n"
            
            # 2. 生成并插入插图 (Visuals)
            if visuals:
                self.log(f"    - 检测到 {len(visuals)} 个可视化概念，准备生成插图...")
                for item in visuals:
                    concept = item.get("concept", "Concept")
                    prompt = item.get("prompt", "")
                    if prompt:
                        self.log(f"      -> 生成插图: {concept}...")
                        img_path = self.image_gen.generate_image(prompt, self.output_dir)
                        if img_path:
                            rel_path = os.path.basename(img_path)
                            final_content += f"\n![{concept}]({rel_path})\n*图示：{concept}*\n"
                            self.generated_images.append(img_path)
            
            final_content += content
            
            return final_content, prompts if prompts else visuals
            
        except json.JSONDecodeError:
            self.log("⚠️ 无法解析 LLM 的 JSON 响应，将返回原始文本。")
            return raw_response, []
        except Exception as e:
            self.log(f"⚠️ 处理响应时出错: {e}")
            return raw_response, []

    def step_market_analysis(self, brief) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的市场分析。" # Fallback
        prompt = self._get_prompt('market_analyst', default_prompt, brief=brief, knowledge=self.knowledge_base)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat_completion(messages)
        return self._process_llm_json_response(response)

    def step_visual_research(self, brief, market_analysis) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的视觉调研。" # Fallback
        prompt = self._get_prompt('visual_researcher', default_prompt, brief=brief, market_analysis=market_analysis, knowledge=self.knowledge_base)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat_completion(messages)
        return self._process_llm_json_response(response)

    def step_design_generation(self, brief, market_analysis, visual_research) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的设计方案。" # Fallback
        prompt = self._get_prompt('product_designer', default_prompt, brief=brief, market_analysis=market_analysis, visual_research=visual_research, knowledge=self.knowledge_base)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat_completion(messages)
        return self._process_llm_json_response(response)

    def step_image_generation(self, prompts_list: List[Dict]):
        """
        根据 Prompts 列表生成图片 (并行)
        """
        if not prompts_list:
            self.log("    ⚠️ 未检测到有效 Prompt，跳过绘图。")
            return

        # 提取 prompt 文本
        clean_prompts = []
        for item in prompts_list:
            p = item.get("prompt", "")
            if p:
                clean_prompts.append(p)
        
        if not clean_prompts:
            return

        total = len(clean_prompts)
        self.log(f"    - 准备并行生成 {total} 张方案图...")
        
        def generate_single(p):
            try:
                return self.image_gen.generate_image(p, self.output_dir)
            except Exception as e:
                self.log(f"Error generating image: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_single, p) for p in clean_prompts]
            for future in concurrent.futures.as_completed(futures):
                img_path = future.result()
                if img_path:
                    self.log(f"      -> 图片已保存: {os.path.basename(img_path)}")
                    self.generated_images.append(img_path)

    # 保留旧的内部方法名以兼容（如果有其他地方调用），但指向新方法
    _step_market_analysis = step_market_analysis
    _step_visual_research = step_visual_research
    _step_design_generation = step_design_generation

    # 旧的 _step_image_generation 逻辑不再适用新的 JSON 结构，
    # 但为了兼容 web_app 可能的调用，我们需要保留一个适配器
    def _step_image_generation(self, design_proposals):
        # 如果 web_app 还在传文本进来，我们尝试用旧逻辑正则提取?
        # 或者 web_app 应该更新为传递 prompts_list
        # 这里先保留旧逻辑作为 fallback，或者打印警告
        pass

    def _save_intermediate(self, filename, content):
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def _save_report(self, brief, p1, p2, p3):
        filename = f"Full_Design_Report.md"
        filepath = os.path.join(self.output_dir, filename)
        
        content = f"""# AI 设计工作流报告

## 项目需求
{brief}

## 第一阶段：市场分析
{p1}

## 第二阶段：视觉调研与痛点分析
{p2}

## 第三阶段：设计方案与 Prompts
{p3}

---
*Generated by AI Design Workflow at {datetime.now()}*
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

def main():
    # 1. 读取配置
    config_path = "CONFIG.md"
    custom_config = {}
    if os.path.exists(config_path):
        print(f"📖 读取系统配置: {config_path}")
        custom_config = md_parser.parse_config_md(config_path)
    else:
        print("⚠️ 未找到 CONFIG.md，使用默认配置")

    # 2. 读取需求
    request_path = "REQUEST.md"
    if len(sys.argv) > 1:
        # 支持命令行覆盖
        brief = sys.argv[1]
        project_name = f"manual_run_{int(time.time())}"
    elif os.path.exists(request_path):
        print(f"📖 读取用户需求: {request_path}")
        req_data = md_parser.parse_request_md(request_path)
        brief = req_data['description']
        project_name = req_data['project_name']
        
        if not brief:
            print("❌ 错误: REQUEST.md 中未找到详细需求描述。")
            return
    else:
        print("请输入设计需求 (例如: '设计一款中高端的实木相框')")
        brief = input("> ")
        project_name = f"manual_run_{int(time.time())}"

    # 3. 创建项目文件夹
    # 处理不合法的文件名字符
    safe_project_name = "".join([c for c in project_name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip()
    safe_project_name = safe_project_name.replace(' ', '_')
    
    project_dir = os.path.join("projects", safe_project_name)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
        print(f"📂 创建项目文件夹: {project_dir}")
    else:
        print(f"📂 使用已有项目文件夹: {project_dir}")
    
    # 4. 运行工作流
    workflow = DesignWorkflow(output_dir=project_dir, custom_config=custom_config)
    workflow.run(brief)

if __name__ == "__main__":
    main()
