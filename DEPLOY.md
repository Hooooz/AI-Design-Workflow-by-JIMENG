# 🚀 AI 设计工作台 - 工业级部署指南

为了让你的 AI 设计工具能够被更多人（客户、团队）稳定访问，我们推荐使用 **GitHub + Vercel + Railway** 的现代全栈部署方案。

## 🔄 版本管理与发布规范 (重要)

为了确保线上版本的稳定性，我们将开发环境与生产环境进行了严格区分。

### 1. 分支策略
*   **`dev` 分支 (线下/开发环境)**: 
    *   所有新功能、代码修复都在此分支进行。
    *   我会在此分支协助你进行开发和本地测试。
*   **`main` 分支 (线上/生产环境)**: 
    *   仅用于存放经过验证、准备上线的代码。
    *   **发布上线必须经过你的明确同意。**

### 2. 发布流程
1.  **开发**: 我在 `dev` 分支完成代码编写。
2.  **验证**: 你在本地运行 `dev` 分支代码进行测试。
3.  **申请发布**: 当功能完善后，我会向你发起“发布申请”。
4.  **确认与合并**: 得到你的同意后，我会将 `dev` 合并到 `main` 并推送，从而触发 Railway 和 Vercel 的线上自动部署。

### 3. 环境区分
后端代码会自动识别环境变量 `ENV`：
*   **线下 (Development)**: `ENV=development`。会使用本地绝对路径，方便在 IDE 中直接运行。
*   **线上 (Production)**: `ENV=production`。会切换为云端兼容的路径模式。
*   *注意：请确保在 Railway 的 Variables 中设置 `ENV=production`。*

---

## 🏗️ 整体架构
*   **前端 (UI)**: [Next.js](https://nextjs.org/) - 部署在 **Vercel**。
*   **后端 (API)**: [FastAPI](https://fastapi.tiangolo.com/) - 部署在 **Railway**。
*   **代码托管**: **GitHub** (自动触发构建与发布)。

### 💡 核心开发规范 (关键)
为了确保云端部署成功，请遵循以下导入规范：
1.  **绝对导入**: 所有模块导入必须以 `src` 开头。
    *   ✅ 正确：`from src import config`
    *   ❌ 错误：`import config`
2.  **根目录执行**: 后端启动时必须在项目根目录下运行。
3.  **环境变量**: 敏感信息（API Key 等）严禁写死在代码中，必须通过 Railway/Vercel 的控制面板配置。

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
