# AI 设计工作流 (AI Design Workflow)

这是一个基于 Python 的自动化设计工作流，旨在辅助设计师完成从「需求分析」到「方案构思」再到「绘图 Prompt 生成」的全过程。

该工具实现了以下核心 Agent 协作流程：
1.  **Market Analyst (市场分析师)**: 分析市场趋势、用户画像与核心关键词。
2.  **Visual Researcher (视觉研究员)**: 寻找视觉参考风格，分析竞品痛点与改进机会。
3.  **Product Designer (产品设计总监)**: 综合以上信息，输出具体设计方案及 AI 绘图提示词 (Midjourney/Stable Diffusion)。

## 快速开始

### 1. 环境准备
确保已安装 Python 3.8+。
安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key
打开 `src/config.py`，填入你的 OpenAI API Key。
```python
OPENAI_API_KEY = "sk-..."
```
> **注意**: 如果没有配置 API Key，系统将自动进入 **Mock 模式**，使用预设数据演示流程。

### 3. 运行工作流
在项目根目录下运行：

```bash
# 方式一：命令行参数输入 Brief
python3 src/main.py "设计一款针对年轻女性的中高端相框，要求有创意"

# 方式二：交互式输入
python3 src/main.py
```

### 4. 查看结果
运行完成后，完整的设计报告（Markdown 格式）将保存在 `output/` 目录下。

## 进阶使用
- **Prompt 优化**: 你可以在 `src/main.py` 中修改各个 Agent 的 Prompt 模板，以适应不同的设计领域（如平面设计、UI 设计）。
- **模型切换**: 在 `src/config.py` 中可以切换模型为 `gpt-3.5-turbo` 或其他兼容模型。

## 目录结构
```
.
├── requirements.txt
├── README.md
├── output/              # 生成的报告存放位置
└── src/
    ├── main.py          # 主程序与 Agent 编排逻辑
    ├── llm_wrapper.py   # LLM 调用封装 (含 Mock 逻辑)
    └── config.py        # 配置文件
```
