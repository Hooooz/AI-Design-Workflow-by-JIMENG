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
import md_parser


class DesignWorkflowError(Exception):
    """设计工作流基础异常类"""

    def __init__(self, message: str, step: str = None, recoverable: bool = False):
        self.message = message
        self.step = step
        self.recoverable = recoverable
        super().__init__(self.message)


class MarketAnalysisError(DesignWorkflowError):
    """市场分析阶段错误"""

    def __init__(self, message: str):
        super().__init__(message, step="market_analysis", recoverable=True)


class VisualResearchError(DesignWorkflowError):
    """视觉研究阶段错误"""

    def __init__(self, message: str):
        super().__init__(message, step="visual_research", recoverable=True)


class DesignGenerationError(DesignWorkflowError):
    """方案设计阶段错误"""

    def __init__(self, message: str):
        super().__init__(message, step="design_generation", recoverable=True)


class ImageGenerationError(DesignWorkflowError):
    """图片生成阶段错误"""

    def __init__(self, message: str):
        super().__init__(message, step="image_generation", recoverable=True)


class DesignWorkflow:
    def __init__(self, output_dir=None, custom_config=None):
        self.custom_config = custom_config or {}
        # 优先使用 custom_config 中的 api_key
        api_key = self.custom_config.get("OPENAI_API_KEY")
        base_url = self.custom_config.get("OPENAI_BASE_URL")

        self.llm = LLMService(api_key=api_key, base_url=base_url)

        # 初始化绘图服务
        jimeng_script = (
            self.custom_config.get("JIMENG_SERVER_SCRIPT")
            or config.JIMENG_SERVER_SCRIPT
        )
        self.image_gen = ImageGenService(server_script_path=jimeng_script)

        self.history = []
        self.generated_images = []

        self.output_dir = output_dir or config.OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 设置默认模型
        self.model = self.custom_config.get("DEFAULT_MODEL", config.DEFAULT_MODEL)

        # 加载外部知识库
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self):
        """
        加载 KNOWLEDGE.md 内容
        """
        kb_path = "KNOWLEDGE.md"
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                print(f"📚 已加载外部知识库: {kb_path}")
                return f.read()
        else:
            print("⚠️ 未找到知识库文件 KNOWLEDGE.md")
            return "暂无外部知识库。"

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run(self, product_brief: str):
        self.log(f"🚀 启动 AI 设计工作流，目标任务: {product_brief}")

        try:
            # Step 1: 市场与竞品分析
            self.log("🔍 Agent 1 (Market Analyst) 正在进行市场趋势分析...")
            market_analysis, _ = self.step_market_analysis(product_brief)
            self.log("✅ 市场分析完成")
            self._save_intermediate("1_Market_Analysis.md", market_analysis)

            # Step 2: 视觉参考与痛点挖掘
            self.log("🎨 Agent 2 (Visual Researcher) 正在寻找视觉参考并分析痛点...")
            visual_research, _ = self.step_visual_research(
                product_brief, market_analysis
            )
            self.log("✅ 视觉调研完成")
            self._save_intermediate("2_Visual_Research.md", visual_research)

            # Step 3: 方案生成与 Prompt 输出
            self.log("💡 Agent 3 (Product Designer) 正在构思设计方案与绘图 Prompt...")
            design_proposals, design_prompts = self.step_design_generation(
                product_brief, market_analysis, visual_research
            )
            self.log("✅ 设计方案生成完成")
            self._save_intermediate("3_Design_Proposals.md", design_proposals)

            # Step 4: 调用即梦生成图片
            self.log("🎨 Agent 4 (Image Generator) 正在根据方案生成概念图...")
            self.step_image_generation(design_prompts)
            self.log("✅ 图片生成完成")

            # Step 5: 生成报告（重新读取包含图片路径的 JSON）
            self.log("📝 正在生成最终设计报告...")
            # 重新读取更新后的 JSON（包含 image_path）
            json_path = os.path.join(self.output_dir, "3_Design_Proposals.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    updated_design_data = json.load(f)
                # 转换为 JSON 字符串，与 step_design_generation 的返回格式一致
                design_proposals_with_images = json.dumps(updated_design_data, ensure_ascii=False)
            else:
                # 如果 JSON 不存在，使用原始数据
                design_proposals_with_images = design_proposals

            report_path = self._save_report(
                product_brief, market_analysis, visual_research, design_proposals_with_images
            )
            self.log(f"📄 完整设计报告已保存至: {report_path}")

        except MarketAnalysisError as e:
            self.log(f"❌ 市场分析失败: {e.message}")
            raise
        except VisualResearchError as e:
            self.log(f"❌ 视觉研究失败: {e.message}")
            raise
        except DesignGenerationError as e:
            self.log(f"❌ 方案设计失败: {e.message}")
            raise
        except ImageGenerationError as e:
            self.log(f"❌ 图片生成失败: {e.message}")
            raise
        except Exception as e:
            self.log(f"❌ 未知错误: {e}")
            raise DesignWorkflowError(f"工作流执行失败: {str(e)}", recoverable=False)

    def _get_prompt(self, agent_name, default_template, **kwargs):
        """
        获取 Prompt，优先使用 CONFIG.md 中的配置
        """
        prompts = self.custom_config.get("prompts", {})
        template = prompts.get(agent_name, default_template)

        # 自动注入 knowledge 参数，如果模板中有 {knowledge} 占位符
        if "{knowledge}" in template and "knowledge" not in kwargs:
            kwargs["knowledge"] = self.knowledge_base

        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.log(f"⚠️ Prompt 模板参数缺失: {e}，将使用默认模板")
            return default_template.format(**kwargs)

    def _process_llm_json_response(
        self, raw_response: str
    ) -> Tuple[str, List[Dict], Dict]:
        """
        解析 LLM 的 JSON 响应，生成插图，并返回格式化的 Markdown、数据列表和原始数据
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

            # 清理 JSON 字符串中的控制字符
            json_str = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str)
            # 处理转义字符问题
            json_str = json_str.replace("\\n", " ").replace("\\r", " ")

            data = json.loads(json_str)

            summary = data.get("summary", "")
            content = data.get("content", "")
            visuals = data.get("visuals", [])
            prompts = data.get("prompts", [])  # For step 3

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
                        img_path = self.image_gen.generate_image(
                            prompt, self.output_dir
                        )
                        if img_path:
                            # 修复：如果是 Supabase URL，直接使用；如果是本地路径，才计算相对路径
                            if img_path.startswith("http"):
                                img_url = img_path
                            else:
                                img_url = os.path.relpath(img_path, self.output_dir)

                            final_content += (
                                f"\n![{concept}]({img_url})\n*图示：{concept}*\n"
                            )
                            self.generated_images.append(img_path)
                            # 修复：确保直接保存 Supabase URL，而非强制转换为损坏的本地路径
                            if img_path.startswith("http"):
                                item["image_path"] = img_path
                            else:
                                item["image_path"] = (
                                    f"/projects/{os.path.basename(self.output_dir)}/{os.path.basename(img_path)}"
                                )

            final_content += content

            return final_content, prompts if prompts else visuals, data

        except json.JSONDecodeError as e:
            self.log(f"⚠️ JSON 解析错误: {e}")
            raise DesignGenerationError(f"无法解析 LLM 的 JSON 响应: {e}")
        except Exception as e:
            self.log(f"⚠️ 处理响应时出错: {e}")
            raise DesignGenerationError(f"处理响应时出错: {e}")

    def step_market_analysis(self, brief, stream=False) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的市场分析。"  # Fallback
        prompt = self._get_prompt(
            "market_analyst", default_prompt, brief=brief, knowledge=self.knowledge_base
        )
        messages = [{"role": "user", "content": prompt}]

        if stream:
            return self.llm.chat_completion_stream(messages)

        response = self.llm.chat_completion(messages)
        try:
            md, prompts, data = self._process_llm_json_response(response)
        except DesignGenerationError:
            # 如果 JSON 解析失败，使用原始响应
            md = response
            prompts = []
            data = {}

        # 保存 JSON 原始数据
        if data:
            self._save_intermediate(
                "1_Market_Analysis.json", json.dumps(data, ensure_ascii=False, indent=2)
            )
        return md, prompts

    def step_visual_research(
        self, brief, market_analysis, stream=False
    ) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的视觉调研。"  # Fallback
        prompt = self._get_prompt(
            "visual_researcher",
            default_prompt,
            brief=brief,
            market_analysis=market_analysis,
            knowledge=self.knowledge_base,
        )
        messages = [{"role": "user", "content": prompt}]

        if stream:
            return self.llm.chat_completion_stream(messages)

        response = self.llm.chat_completion(messages)
        try:
            md, prompts, data = self._process_llm_json_response(response)
        except DesignGenerationError:
            md = response
            prompts = []
            data = {}

        if data:
            self._save_intermediate(
                "2_Visual_Research.json", json.dumps(data, ensure_ascii=False, indent=2)
            )
        return md, prompts

    def step_design_generation(
        self,
        brief,
        market_analysis,
        visual_research,
        image_count=4,
        persona="",
        stream=False,
    ) -> Tuple[str, List]:
        default_prompt = "请输出 JSON 格式的设计方案。"  # Fallback

        # 构造 Persona 指令
        persona_instruction = ""
        if persona:
            persona_instruction = f"\n特别注意：请以【{persona}】的专业视角进行设计构思。在描述方案细节时，重点关注该角色重视的领域（如材质、结构、光影或场景氛围等）。\n"

        # 构造数量指令
        count_instruction = f"\n请生成 {image_count} 个不同的设计方案/Prompt。"

        # 获取基础 Prompt
        base_prompt = self._get_prompt(
            "product_designer",
            default_prompt,
            brief=brief,
            market_analysis=market_analysis,
            visual_research=visual_research,
            knowledge=self.knowledge_base,
            image_count=image_count,
        )

        # 拼接完整 Prompt
        full_prompt = base_prompt + persona_instruction

        messages = [{"role": "user", "content": full_prompt}]

        if stream:
            return self.llm.chat_completion_stream(messages)

        response = self.llm.chat_completion(messages)
        try:
            md, prompts, data = self._process_llm_json_response(response)
        except DesignGenerationError:
            md = response
            prompts = []
            data = {}

        if data:
            self._save_intermediate(
                "3_Design_Proposals.json",
                json.dumps(data, ensure_ascii=False, indent=2),
            )
            # Return JSON string instead of markdown to allow frontend to render rich card view
            return json.dumps(data, ensure_ascii=False), prompts
        return md, prompts

    def step_image_generation(
        self, prompts_list: List[Dict], session_id=None, skip_json_update=False
    ):
        """
        根据 Prompts 列表生成图片 (并行)，并更新对应的 JSON 文件和数据库
        """
        if not prompts_list:
            self.log("    ⚠️ 未检测到有效 Prompt，跳过绘图。")
            return

        # 提取有效 prompt 及其索引
        valid_tasks = []  # (index, prompt_text)
        for i, item in enumerate(prompts_list):
            p = item.get("prompt", "")
            if p:
                valid_tasks.append((i, p))

        if not valid_tasks:
            return

        total = len(valid_tasks)
        self.log(
            f"    - 准备并行生成 {total} 张方案图 (SessionID: {'Yes' if session_id else 'No'})..."
        )

        def generate_single(p):
            try:
                return self.image_gen.generate_image(
                    p, self.output_dir, session_id=session_id
                )
            except Exception as e:
                self.log(f"Error generating image: {e}")
                return None

        # 获取最大并发数
        max_workers = getattr(config, "MAX_CONCURRENT_IMAGES", 3)
        max_workers = min(max_workers, len(valid_tasks))

        # 使用 future 映射来保持结果与原始列表的对应关系
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # map future to index
            future_to_index = {
                executor.submit(generate_single, p): idx for idx, p in valid_tasks
            }

            for future in concurrent.futures.as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    img_path = future.result()
                    if img_path:
                        # 检查是否是 Supabase Storage URL
                        if img_path.startswith("http"):
                            # 使用 Supabase Storage URL
                            self.log(f"      -> 图片已保存到云端: {img_path[:80]}...")
                            self.generated_images.append(img_path)
                            prompts_list[idx]["image_path"] = img_path
                        else:
                            # 本地路径，构建相对路径
                            self.log(
                                f"      -> 图片已保存: {os.path.basename(img_path)}"
                            )
                            self.generated_images.append(img_path)
                            rel_path = f"/projects/{os.path.basename(self.output_dir)}/{os.path.basename(img_path)}"
                            prompts_list[idx]["image_path"] = rel_path
                except Exception as e:
                    self.log(f"      -> 生成失败 (Index {idx}): {e}")

        if skip_json_update:
            return

        # 尝试更新 3_Design_Proposals.json 和数据库
        json_path = os.path.join(self.output_dir, "3_Design_Proposals.json")
        updated_data = None

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 更新 data 中的 prompts
                # 注意：prompts_list 是从 data['prompts'] 提取出来的，引用可能已断开（如果经过了序列化/反序列化）
                # 但在这里我们直接修改了 data 中的对应结构，因为我们知道结构是 {'prompts': [...]}
                if "prompts" in data and isinstance(data["prompts"], list):
                    # 按照索引合并 image_path
                    for i, item in enumerate(prompts_list):
                        if i < len(data["prompts"]):
                            if "image_path" in item:
                                data["prompts"][i]["image_path"] = item["image_path"]

                # 回写文件
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.log("✅ 已更新 Design Proposals JSON 文件中的图片路径")

                updated_data = data

            except Exception as e:
                self.log(f"⚠️ 更新 JSON 文件失败: {e}")

        # 同步到数据库
        try:
            # 使用局部导入避免循环依赖
            from . import api as api_module

            # 获取数据库中的现有内容
            db_proj = api_module.db_get_project(os.path.basename(self.output_dir))
            existing_content = db_proj.get("content", {}) if db_proj else {}

            # 更新 design_proposals 字段
            if updated_data:
                existing_content["design_proposals"] = json.dumps(
                    updated_data, ensure_ascii=False, indent=2
                )
            else:
                # 即使 JSON 文件更新失败，也尝试同步 prompts_list 中的 image_path
                if "design_proposals" in existing_content:
                    try:
                        existing_proposals = json.loads(
                            existing_content["design_proposals"]
                        )
                        if "prompts" in existing_proposals:
                            for i, item in enumerate(prompts_list):
                                if (
                                    i < len(existing_proposals["prompts"])
                                    and "image_path" in item
                                ):
                                    existing_proposals["prompts"][i]["image_path"] = (
                                        item["image_path"]
                                    )
                            existing_content["design_proposals"] = json.dumps(
                                existing_proposals, ensure_ascii=False, indent=2
                            )
                    except (json.JSONDecodeError, KeyError):
                        pass

            # 保存到数据库
            api_module.save_project_content(
                os.path.basename(self.output_dir), existing_content
            )
            self.log("✅ 已同步图片路径到数据库")

            # 保存图片列表到数据库
            if self.generated_images:
                # 构建前端可访问的图片路径
                # 注意：如果是 Supabase URL，直接使用；如果是本地路径，构建相对路径
                image_paths = []
                for p in self.generated_images:
                    if p.startswith("http"):
                        # Supabase Storage URL，直接使用
                        image_paths.append(p)
                    else:
                        # 本地路径，构建相对路径
                        image_paths.append(
                            f"/projects/{os.path.basename(self.output_dir)}/{os.path.basename(p)}"
                        )
                api_module.save_project_images(
                    os.path.basename(self.output_dir), image_paths
                )
                self.log("✅ 已保存图片列表到数据库")

        except Exception as e:
            self.log(f"⚠️ 同步数据库失败: {e}")

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
        # 安全文件名
        safe_filename = "".join(
            [
                c
                for c in filename
                if c.isalpha() or c.isdigit() or c in (" ", "_", "-", ".")
            ]
        ).strip()
        filepath = os.path.join(self.output_dir, safe_filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def _save_report(self, brief, p1, p2, p3):
        filename = f"Full_Design_Report.md"
        filepath = os.path.join(self.output_dir, filename)

        # 处理第三阶段的内容：将 JSON 转换为带图片的 Markdown
        p3_content = p3
        try:
            # 尝试解析 p3 作为 JSON（因为 step_design_generation 返回 JSON 字符串）
            data = json.loads(p3)
            if isinstance(data, dict) and "prompts" in data:
                # 构建带图片的 Markdown
                p3_content = ""
                if "summary" in data:
                    p3_content += f"> 💡 **核心摘要**: {data['summary']}\n\n"

                # 添加每个设计方案及其图片
                for i, prompt_item in enumerate(data["prompts"], 1):
                    scheme = prompt_item.get("scheme", f"方案 {i}")
                    description = prompt_item.get("description", "")
                    inspiration = prompt_item.get("inspiration", "")
                    image_path = prompt_item.get("image_path", "")

                    p3_content += f"\n### 方案 {i}：{scheme}\n\n"
                    if inspiration:
                        p3_content += f"**设计灵感：** {inspiration}\n\n"
                    if description:
                        p3_content += f"{description}\n\n"
                    if image_path:
                        # 处理图片路径
                        if image_path.startswith("http"):
                            # Supabase URL，直接使用
                            img_url = image_path
                        else:
                            # 本地路径，使用文件名
                            img_url = os.path.basename(image_path)
                        p3_content += f"![{scheme}]({img_url})\n\n"
        except (json.JSONDecodeError, ValueError):
            # 如果不是 JSON，使用原始内容
            pass

        content = f"""# AI 设计工作流报告

## 项目需求
{brief}

## 第一阶段：市场分析
{p1}

## 第二阶段：视觉调研与痛点分析
{p2}

## 第三阶段：设计方案与 Prompts
{p3_content}

---
*Generated by AI Design Workflow at {datetime.now()}*
"""
        with open(filepath, "w", encoding="utf-8") as f:
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
        brief = req_data["description"]
        project_name = req_data["project_name"]

        if not brief:
            print("❌ 错误: REQUEST.md 中未找到详细需求描述。")
            return
    else:
        print("请输入设计需求 (例如: '设计一款中高端的实木相框')")
        brief = input("> ")
        project_name = f"manual_run_{int(time.time())}"

    # 3. 创建项目文件夹
    # 处理不合法的文件名字符
    safe_project_name = "".join(
        [c for c in project_name if c.isalpha() or c.isdigit() or c in (" ", "_", "-")]
    ).strip()
    safe_project_name = safe_project_name.replace(" ", "_")

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
