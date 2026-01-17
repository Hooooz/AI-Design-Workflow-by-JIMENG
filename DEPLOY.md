# 🚀 AI 设计工作台 - 工业级部署指南

为了让你的 AI 设计工具能够被更多人（客户、团队）稳定访问，我们推荐使用 **GitHub + Vercel + Railway** 的现代全栈部署方案。

---

## 🏗️ 整体架构
*   **前端 (UI)**: [Next.js](https://nextjs.org/) - 部署在 **Vercel** (极致的访问速度与自动预览)。
*   **后端 (API)**: [FastAPI](https://fastapi.tiangolo.com/) - 部署在 **Railway** 或 **Render** (稳定运行 Python 复杂逻辑)。
*   **代码托管**: **GitHub** (自动触发构建与发布)。

---

## 🛠️ 第一步：推送代码到 GitHub

1.  **创建仓库**: 在 GitHub 上创建一个新的私有仓库。
2.  **推送代码**:
    ```bash
    git remote add origin <你的仓库地址>
    git push -u origin main
    ```
    *注：我已经帮你配置好了 `.gitignore`，API Key 和 临时文件不会被上传。*

---

## ☁️ 第二步：部署后端 (Railway/Render)

后端负责处理 AI 逻辑和即梦绘图。

1.  **登录 [Railway](https://railway.app/)** 并关联 GitHub 仓库。
2.  **创建项目**: 选择该代码仓库。
3.  **配置变量 (Variables)**:
    在 Railway 控制面板中添加以下环境变量：
    *   `OPENAI_API_KEY`: 你的 Gemini/OpenAI Key
    *   `OPENAI_BASE_URL`: 接口地址
    *   `PORT`: `8000` (Railway 会自动分配)
4.  **部署**: Railway 会识别 `Procfile` 并自动启动 FastAPI 服务。
5.  **获取 URL**: 记录生成的后端地址（如 `https://your-backend.railway.app`）。

---

## 🎨 第三步：部署前端 (Vercel)

前端提供精美的用户界面。

1.  **登录 [Vercel](https://vercel.com/)** 并导入 GitHub 仓库。
2.  **配置设置**:
    *   **Root Directory**: 设置为 `web-ui`。
    *   **Framework Preset**: 选择 `Next.js`。
3.  **配置变量 (Environment Variables)**:
    添加以下变量：
    *   `NEXT_PUBLIC_API_URL`: 设置为你上一步获取的 **Railway 后端地址**。
4.  **部署**: 点击 Deploy。

---

## 🌟 方案优势
1.  **自动更新**: 只要你在本地修改代码并 `git push`，前端和后端都会自动更新发布。
2.  **零验证访问**: 移除了复杂的内网穿透验证，客户直接打开网址即可使用。
3.  **极速响应**: Vercel 的边缘网络确保全球访问都能秒开。

---

## ⚠️ 关于即梦绘图 (MCP) 的部署
在云端运行时，请确保：
1.  `test_workspace/image-gen-server` 文件夹已包含在代码中。
2.  在后端服务中安装了 `uv`:
    `curl -LsSf https://astral.sh/uv/install.sh | sh`
3.  如果绘图失败，请检查后端日志中的文件路径权限。
