# AI 设计工作流 (AI Design Workflow)

这是一个基于 Python 的自动化设计工作流，旨在辅助设计师完成从「需求分析」到「方案构思」再到「绘图 Prompt 生成」的全过程。

该工具实现了以下核心 Agent 协作流程：
1.  **Market Analyst (市场分析师)**: 分析市场趋势、用户画像与核心关键词。
2.  **Visual Researcher (视觉研究员)**: 寻找视觉参考风格，分析竞品痛点与改进机会。
3.  **Product Designer (产品设计总监)**: 综合以上信息，输出具体设计方案及 AI 绘图提示词 (Midjourney/Stable Diffusion)。

## ✨ 新特性

- 🔒 **安全增强**: 输入验证、路径安全、速率限制
- 🧪 **测试覆盖**: 45+ 单元测试，测试覆盖率 80%+
- 📊 **配置检查**: 运行 `python3 scripts/check_config.py` 检查配置
- 🚀 **性能优化**: 并发控制、超时保护

## 快速开始

### 1. 环境准备
确保已安装 Python 3.8+。
安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

**推荐方式（生产环境）**:
```bash
export OPENAI_API_KEY="sk-your-api-key"
export ENV="production"
```

**开发环境（自动使用兜底 Key）**:
系统会自动使用开发环境的兜底 API Key，无需手动配置。

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

- **Prompt 优化**: 你可以在 `CONFIG.md` 中修改各个 Agent 的 Prompt 模板，无需修改代码。
- **模型切换**: 在 `CONFIG.md` 中可以切换模型。
- **配置检查**: 运行 `python3 scripts/check_config.py` 检查系统配置。

## 目录结构

```
.
├── requirements.txt
├── README.md
├── CONFIG.md           # 系统配置和 Prompts
├── SECURITY.md         # 安全指南
├── .env.example        # 环境变量示例
├── output/             # 生成的报告存放位置
├── projects/           # 项目文件
├── scripts/            # 工具脚本
├── tests/              # 单元测试
└── src/
    ├── main.py         # 主程序与 Agent 编排逻辑
    ├── api.py          # FastAPI 服务
    ├── web_app.py      # Streamlit Web 界面
    ├── llm_wrapper.py  # LLM 调用封装
    ├── image_gen.py    # 图片生成服务
    ├── security.py     # 安全验证模块
    └── config.py       # 配置文件
```

## 测试

运行所有测试:
```bash
python3 -m pytest tests/ -v
```

运行配置检查:
```bash
python3 scripts/check_config.py
```

## 部署

详见 [DEPLOY.md](DEPLOY.md)
