import streamlit as st
import os
import sys
import time
import re
import json
import concurrent.futures
from datetime import datetime
import shutil

# 添加 src 到路径以便导入模块
sys.path.append(os.path.dirname(__file__))

from main import DesignWorkflow
import config
import md_parser

# 设置页面配置
st.set_page_config(
    page_title="AI 设计工作流 (AI Design Workflow)",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown(
    """
<style>
    .report-content {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: none;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1a1a1a; /* 强制字体颜色为深色 */
    }
    .stButton>button {
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #1a1a1a; /* 确保按钮文字颜色为深色 */
        background-color: #ffffff; /* 确保背景为白色 */
        border: 1px solid #e0e0e0;
    }
    /* 针对 markdown 容器内的所有文本强制深色 */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {
        color: #1a1a1a !important;
    }
    /* 修复 Tab 标签页内的文本颜色 */
    .stTabs [data-baseweb="tab"] {
         color: #1a1a1a !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    h1, h2, h3 {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #1a1a1a;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-radius: 8px;
        padding: 4px;
        background-color: #f1f5f9;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .sidebar-content {
        padding: 1rem;
        border-radius: 8px;
        background: #f8fafc;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


class StreamlitLogger:
    """
    适配器：将 DesignWorkflow 的日志重定向到 Streamlit 界面
    """

    def __init__(self, log_container):
        self.log_container = log_container
        self.logs = []

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)

        # 实时更新 UI
        if self.log_container:
            with self.log_container:
                # 只显示最近的 10 条日志
                log_text = "\n".join(self.logs[-10:])
                st.code(log_text, language="text")


class WebDesignWorkflow(DesignWorkflow):
    """
    继承 DesignWorkflow，适配 Web 端交互
    """

    def __init__(self, output_dir, custom_config, logger):
        super().__init__(output_dir, custom_config)
        self.logger = logger
        # 复用父类的 generated_images

    def log(self, message):
        self.logger.log(message)

    # 重写 step_image_generation 以支持 Streamlit 进度条
    def step_image_generation(self, prompts_list):
        if not prompts_list:
            self.log("    ⚠️ 未检测到有效 Prompt，跳过绘图。")
            return

        clean_prompts = [p.get("prompt", "") for p in prompts_list if p.get("prompt")]
        if not clean_prompts:
            return

        total = len(clean_prompts)
        self.log(f"    - 准备并行生成 {total} 张方案图...")

        progress_bar = st.progress(0, text="正在生成图片...")
        completed = 0

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

                completed += 1
                progress_bar.progress(
                    completed / total, text=f"正在生成第 {completed}/{total} 张图片..."
                )

        progress_bar.empty()


def init_session_state():
    defaults = {
        "project_name": "Polaroid_Bag_Design",
        "brief": "做一款拍立得相机包，需要参考市场中高端品牌的女性包包去结合设计一些相机包",
        "market_analysis": "",
        "visual_research": "",
        "design_proposals": "",
        "design_prompts": [],
        "generated_images": [],
        "full_report": "",
        "logs": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_history_project(project_name):
    """
    加载历史项目数据到 Session State
    """
    root_dir = os.path.dirname(os.path.dirname(__file__))
    project_dir = os.path.join(root_dir, "projects", project_name)

    if not os.path.exists(project_dir):
        st.error(f"项目 {project_name} 不存在")
        return

    st.session_state.project_name = project_name

    # 尝试加载各个 Markdown 文件
    def read_file(fname):
        path = os.path.join(project_dir, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    st.session_state.market_analysis = read_file("1_Market_Analysis.md")
    st.session_state.visual_research = read_file("2_Visual_Research.md")
    st.session_state.design_proposals = read_file("3_Design_Proposals.md")
    st.session_state.full_report = read_file("Full_Design_Report.md")

    # 尝试加载图片
    # 扫描目录下所有 jpg/png
    images = []
    for f in os.listdir(project_dir):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            images.append(os.path.join(project_dir, f))

    # 按时间排序图片（如果文件名包含时间戳）
    images.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    # 使用绝对路径
    st.session_state.generated_images = [os.path.abspath(p) for p in images]

    st.success(f"已加载项目: {project_name}")


def get_workflow(project_dir, model_name, log_container=None):
    root_dir = os.path.dirname(os.path.dirname(__file__))
    custom_config = {
        "OPENAI_API_KEY": config.OPENAI_API_KEY,
        "OPENAI_BASE_URL": config.OPENAI_BASE_URL,
        "DEFAULT_MODEL": model_name,
        "prompts": md_parser.parse_config_md(os.path.join(root_dir, "CONFIG.md")).get(
            "prompts", {}
        ),
    }
    logger = StreamlitLogger(log_container)
    return WebDesignWorkflow(project_dir, custom_config, logger)


def main():
    st.title("🎨 AI 设计工作流 (AI Design Workflow)")
    st.markdown("基于 Gemini 和 Jimeng 的全自动设计助手")

    init_session_state()

    # --- 侧边栏配置 ---
    with st.sidebar:
        # 1. 历史项目 (History)
        st.header("📂 历史项目")

        # 扫描 projects 文件夹
        root_dir = os.path.dirname(os.path.dirname(__file__))
        projects_dir = os.path.join(root_dir, "projects")

        existing_projects = []
        if os.path.exists(projects_dir):
            existing_projects = [
                d
                for d in os.listdir(projects_dir)
                if os.path.isdir(os.path.join(projects_dir, d))
            ]
            # 按修改时间倒序排列
            existing_projects.sort(
                key=lambda x: os.path.getmtime(os.path.join(projects_dir, x)),
                reverse=True,
            )

        selected_project = st.selectbox(
            "选择历史项目加载", ["-- 新建项目 --"] + existing_projects, index=0
        )

        if selected_project != "-- 新建项目 --":
            if st.button("📂 加载选中项目"):
                load_history_project(selected_project)

        st.divider()

        st.header("⚙️ 系统配置")

        model_options = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-2.5-flash",
        ]
        model_name = st.selectbox("模型选择 (Gemini)", model_options, index=0)

        st.divider()
        with st.expander("📚 查看知识库"):
            kb_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "KNOWLEDGE.md"
            )
            if os.path.exists(kb_path):
                with open(kb_path, "r", encoding="utf-8") as f:
                    st.text(f.read())

    # --- 主界面 ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.session_state.project_name = st.text_input(
            "项目名称", value=st.session_state.project_name
        )

    st.session_state.brief = st.text_area(
        "✍️ 请输入设计需求", height=100, value=st.session_state.brief
    )

    # 图片数量设置
    with st.expander("⚙️ 生成设置", expanded=False):
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            image_count = st.number_input(
                "方案图片数量", min_value=1, max_value=12, value=4, step=1
            )
        with col_img2:
            persona = st.text_input(
                "角色视角（可选）", placeholder="如：工业设计师、时尚博主..."
            )

    # 全局运行按钮
    if st.button("🚀 一键生成全流程", type="primary", use_container_width=True):
        st.session_state.logs = []  # 清空旧日志

        root_dir = os.path.dirname(os.path.dirname(__file__))
        project_dir = os.path.join(root_dir, "projects", st.session_state.project_name)

        st.subheader("📝 运行日志")
        log_container = st.empty()
        wf = get_workflow(project_dir, model_name, log_container)

        with st.spinner("AI 正在全速运转中..."):
            # Step 1
            wf.log("开始市场分析...")
            m_analysis, _ = wf.step_market_analysis(st.session_state.brief)
            st.session_state.market_analysis = m_analysis
            wf._save_intermediate("1_Market_Analysis.md", m_analysis)

            # Step 2
            wf.log("开始视觉调研...")
            v_research, _ = wf.step_visual_research(st.session_state.brief, m_analysis)
            st.session_state.visual_research = v_research
            wf._save_intermediate("2_Visual_Research.md", v_research)

            # Step 3
            wf.log("开始方案设计...")
            d_proposals, d_prompts = wf.step_design_generation(
                st.session_state.brief,
                m_analysis,
                v_research,
                image_count=image_count,
                persona=persona,
            )
            st.session_state.design_proposals = d_proposals
            st.session_state.design_prompts = d_prompts
            wf._save_intermediate("3_Design_Proposals.md", d_proposals)

            # Step 4
            wf.log("开始生成最终效果图...")
            wf.step_image_generation(d_prompts)
            st.session_state.generated_images = wf.generated_images  # 更新图片列表

            # Step 5
            report_path = wf._save_report(
                st.session_state.brief, m_analysis, v_research, d_proposals
            )
            st.session_state.full_report = f"报告已生成: {report_path}"

        st.success("全流程任务完成！")

    st.divider()

    # --- 模块化展示与操作 ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 市场分析", "🎨 视觉调研", "💡 方案设计", "🖼️ 最终图库", "📋 完整报告"]
    )

    root_dir = os.path.dirname(os.path.dirname(__file__))
    project_dir = os.path.join(root_dir, "projects", st.session_state.project_name)

    # Tab 1: 市场分析
    with tab1:
        col_t1_1, col_t1_2 = st.columns([4, 1])
        with col_t1_2:
            st.markdown("### 📈 市场分析")
            if st.button("🔄 重新生成", type="secondary", use_container_width=True):
                with st.spinner("🔍 正在分析市场趋势..."):
                    wf = get_workflow(project_dir, model_name)
                    res, _ = wf.step_market_analysis(st.session_state.brief)
                    st.session_state.market_analysis = res
                    wf._save_intermediate("1_Market_Analysis.md", res)
                    st.rerun()

        if st.session_state.market_analysis:
            st.markdown(st.session_state.market_analysis)
        else:
            st.info("📊 暂无市场分析结果，点击上方按钮生成")

    # Tab 2: 视觉调研
    with tab2:
        col_t2_1, col_t2_2 = st.columns([4, 1])
        with col_t2_2:
            st.markdown("### 🎨 视觉调研")
            if st.button("🔄 重新生成", type="secondary", use_container_width=True):
                if not st.session_state.market_analysis:
                    st.error("⚠️ 请先生成市场分析报告")
                else:
                    with st.spinner("🎨 正在寻找视觉参考..."):
                        wf = get_workflow(project_dir, model_name)
                        res, _ = wf.step_visual_research(
                            st.session_state.brief, st.session_state.market_analysis
                        )
                        st.session_state.visual_research = res
                        wf._save_intermediate("2_Visual_Research.md", res)
                        st.rerun()

        if st.session_state.visual_research:
            st.markdown(st.session_state.visual_research)
        else:
            st.info("🎨 暂无视觉调研结果，请先完成市场分析后点击生成")

    # Tab 3: 方案设计
    with tab3:
        col_t3_1, col_t3_2 = st.columns([4, 1])
        with col_t3_2:
            st.markdown("### 💡 方案设计")
            if st.button("🔄 重新生成", type="secondary", use_container_width=True):
                if not st.session_state.visual_research:
                    st.error("⚠️ 请先生成视觉调研报告")
                else:
                    with st.spinner("💡 正在构思设计方案..."):
                        wf = get_workflow(project_dir, model_name)
                        res, prompts = wf.step_design_generation(
                            st.session_state.brief,
                            st.session_state.market_analysis,
                            st.session_state.visual_research,
                        )
                        st.session_state.design_proposals = res
                        st.session_state.design_prompts = prompts
                        wf._save_intermediate("3_Design_Proposals.md", res)
                        st.rerun()

        # 图片数量设置
        with st.expander("⚙️ 方案设置", expanded=False):
            image_count = st.number_input(
                "生成方案数量", min_value=1, max_value=12, value=4, step=1
            )
            persona = st.text_input(
                "角色视角（可选）", placeholder="如：工业设计师、时尚博主..."
            )

        # 展示方案内容
        if st.session_state.design_proposals:
            try:
                # 尝试解析JSON格式的设计方案
                proposals_data = json.loads(st.session_state.design_proposals)
                if isinstance(proposals_data, dict) and "prompts" in proposals_data:
                    prompts_list = proposals_data["prompts"]

                    st.markdown("### 💡 设计方案")

                    for idx, item in enumerate(prompts_list):
                        with st.container():
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                scheme = item.get("scheme", f"方案 {idx + 1}")
                                st.markdown(f"#### {scheme}")

                                # 如果有图片路径，显示图片
                                if "image_path" in item:
                                    img_path = item["image_path"]
                                    if os.path.exists(img_path):
                                        st.image(img_path, use_container_width=True)
                                    elif os.path.exists(
                                        os.path.join(
                                            project_dir, os.path.basename(img_path)
                                        )
                                    ):
                                        st.image(
                                            os.path.join(
                                                project_dir, os.path.basename(img_path)
                                            ),
                                            use_container_width=True,
                                        )

                            with c2:
                                inspiration = item.get("inspiration", "")
                                if inspiration:
                                    st.markdown(f"**🎯 创意源泉**: {inspiration}")

                                description = item.get("description", "")
                                if description:
                                    st.markdown(f"**📝 设计描述**: {description}")

                                prompt = item.get("prompt", "")
                                if prompt:
                                    st.code(prompt, language="text")

                        st.divider()

                    # 保存prompts到session state用于图片生成
                    if prompts_list != st.session_state.design_prompts:
                        st.session_state.design_prompts = prompts_list

                else:
                    st.markdown(st.session_state.design_proposals)
            except json.JSONDecodeError:
                st.markdown(st.session_state.design_proposals)
        else:
            st.markdown("暂无内容，请点击生成。")

        # 在方案底部添加追加功能
        st.divider()
        st.markdown("### ➕ 追加更多方案")
        st.markdown("基于现有设计方案，生成更多差异化变体")

        col_add1, col_add2 = st.columns([1, 3])
        with col_add1:
            add_count = st.number_input(
                "追加数量", min_value=1, max_value=8, value=2, step=1, key="add_count"
            )
        with col_add2:
            add_persona = st.text_input(
                "角色视角（可选）", placeholder="如：工业设计师...", key="add_persona"
            )

        if st.button("🚀 生成追加方案", type="primary"):
            if not st.session_state.design_proposals:
                st.error("请先生成设计方案！")
            else:
                with st.spinner("正在生成追加方案..."):
                    try:
                        wf = get_workflow(project_dir, model_name)

                        # 尝试解析现有方案
                        try:
                            current_proposals = json.loads(
                                st.session_state.design_proposals
                            )
                            if (
                                isinstance(current_proposals, dict)
                                and "prompts" in current_proposals
                            ):
                                current_prompts = current_proposals["prompts"]
                            else:
                                current_prompts = (
                                    st.session_state.design_prompts
                                    if st.session_state.design_prompts
                                    else []
                                )
                        except:
                            current_prompts = (
                                st.session_state.design_prompts
                                if st.session_state.design_prompts
                                else []
                            )

                        # 调用追加方案接口
                        # 这里直接调用模型生成新方案
                        add_persona_instruction = (
                            f"以【{add_persona}】的视角，" if add_persona else ""
                        )

                        from llm_wrapper import LLMService
                        import md_parser as mp

                        root_dir = os.path.dirname(os.path.dirname(__file__))
                        config_path = os.path.join(root_dir, "CONFIG.md")
                        md_config = (
                            mp.parse_config_md(config_path)
                            if os.path.exists(config_path)
                            else {}
                        )
                        prompts_cfg = md_config.get("prompts", {})

                        default_prompt = """
                        基于以下设计方案：
                        {design_proposals}
                        
                        请{add_persona_instruction}再构思 {count} 个新的、有差异化的设计方案变体，并提供对应的绘图 Prompt。
                        请只输出 JSON 格式，包含 `prompts` 列表。
                        """

                        prompt_template = prompts_cfg.get(
                            "variant_generator", default_prompt
                        )

                        # 准备上下文
                        dp_content = (
                            st.session_state.design_proposals[:3000] + "..."
                            if len(st.session_state.design_proposals) > 3000
                            else st.session_state.design_proposals
                        )

                        prompt = prompt_template.format(
                            design_proposals=dp_content,
                            add_persona_instruction=add_persona_instruction,
                            count=add_count,
                        )

                        llm = LLMService(
                            api_key=config.OPENAI_API_KEY,
                            base_url=config.OPENAI_BASE_URL,
                        )

                        messages = [{"role": "user", "content": prompt}]
                        response = llm.chat_completion(messages, model=model_name)

                        # 解析新方案
                        _, new_prompts = wf._process_llm_json_response(response)

                        if new_prompts:
                            # 生成新方案图片
                            wf.step_image_generation(new_prompts)

                            # 合并到现有方案
                            try:
                                current_data = json.loads(
                                    st.session_state.design_proposals
                                )
                                if (
                                    isinstance(current_data, dict)
                                    and "prompts" in current_data
                                ):
                                    current_data["prompts"].extend(new_prompts)
                                    st.session_state.design_proposals = json.dumps(
                                        current_data, ensure_ascii=False
                                    )
                                    st.session_state.design_prompts = current_data[
                                        "prompts"
                                    ]
                                else:
                                    # 如果不是JSON格式，追加到末尾
                                    st.session_state.design_proposals += (
                                        "\n\n### 追加方案\n"
                                    )
                                    for i, p in enumerate(new_prompts):
                                        st.session_state.design_proposals += f"\n#### 方案 {len(st.session_state.design_prompts) + i + 1}\n"
                                        if p.get("scheme"):
                                            st.session_state.design_proposals += (
                                                f"- 名称: {p.get('scheme')}\n"
                                            )
                                        if p.get("prompt"):
                                            st.session_state.design_proposals += (
                                                f"- Prompt: {p.get('prompt')}\n"
                                            )
                                    st.session_state.design_prompts.extend(new_prompts)
                            except:
                                st.session_state.design_prompts.extend(new_prompts)

                            # 更新生成的图片列表
                            st.session_state.generated_images.extend(
                                wf.generated_images
                            )

                            st.success(f"成功生成 {len(new_prompts)} 个追加方案！")
                            st.rerun()
                        else:
                            st.error("未能生成有效方案，请重试")

                    except Exception as e:
                        st.error(f"生成追加方案失败: {e}")

    # Tab 4: 最终图库
    with tab4:
        col_t4_1, col_t4_2 = st.columns([4, 1])
        with col_t4_2:
            st.markdown("### 🖼️ 最终图库")
            if st.button("🎨 重新生成图片", type="secondary", use_container_width=True):
                if not st.session_state.design_prompts:
                    st.error("⚠️ 暂无设计 Prompt，请先生成方案")
                else:
                    with st.spinner("🎨 正在绘制概念图..."):
                        wf = get_workflow(project_dir, model_name)
                        wf.step_image_generation(st.session_state.design_prompts)
                        st.session_state.generated_images.extend(wf.generated_images)
                        st.rerun()
                        # 合并新生成的图片
                        st.session_state.generated_images.extend(wf.generated_images)
                        st.rerun()

        if st.session_state.generated_images:
            cols = st.columns(3)
            for idx, img_path in enumerate(st.session_state.generated_images):
                with cols[idx % 3]:
                    # 确保路径存在且是绝对路径
                    abs_path = os.path.abspath(img_path)
                    if os.path.exists(abs_path):
                        st.image(
                            abs_path, caption=f"Img {idx + 1}", use_container_width=True
                        )

                        # 添加下载按钮
                        with open(abs_path, "rb") as file:
                            btn = st.download_button(
                                label="📥 下载图片",
                                data=file,
                                file_name=os.path.basename(abs_path),
                                mime="image/jpeg",
                                key=f"download_btn_{idx}",
                            )
                    else:
                        st.warning(f"图片文件未找到: {img_path}")
        else:
            st.info("暂无生成的图片")

    # Tab 5: 完整报告
    with tab5:
        if st.button("📄 合成/刷新完整报告"):
            wf = get_workflow(project_dir, model_name)
            report_path = wf._save_report(
                st.session_state.brief,
                st.session_state.market_analysis,
                st.session_state.visual_research,
                st.session_state.design_proposals,
            )
            st.success(f"报告已保存: {report_path}")

            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
                st.markdown(report_content)
                st.download_button("📥 下载 Markdown", report_content, "Full_Report.md")


if __name__ == "__main__":
    main()
