# AI 设计工作流 v2

## 概述

AI设计工作流 v2 是一个稳定、高性能的设计辅助工具，通过重构解决了前后端不稳定的问题。

## 核心改进

### 后端改进
- **统一配置管理**: 单一处配置，支持环境变量覆盖和验证
- **健壮的数据库层**: 自动重连、连接重试、完善的错误处理
- **持久化任务状态**: 使用Supabase存储任务状态，服务重启不丢失
- **结构化日志**: JSON格式日志，便于监控和分析

### 前端改进
- **健壮的API客户端**: 自动重试（指数退避）、超时控制
- **智能轮询**: 自动重连、指数退避、清理函数
- **类型安全的状态管理**: 响应式状态、自动持久化
- **API代理配置**: 解决CORS问题

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 18+
- Supabase账户

### 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行
python -m src.main
```

### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.local
# 编辑 .env.local 文件

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

## 环境变量

### 后端 (.env)

```bash
# 必需
OPENAI_API_KEY=your-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key

# 可选
ENV=development  # 或 production
OPENAI_BASE_URL=https://api.openai.com/v1
PORT=8000
MAX_CONCURRENT_IMAGES=3
```

### 前端 (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 项目结构

```
ai-design-workflow-v2/
├── backend/
│   ├── src/
│   │   ├── core/           # 核心模块
│   │   │   ├── config.py   # 配置管理
│   │   │   └── logger.py   # 日志配置
│   │   ├── services/       # 服务层
│   │   │   ├── database.py # 数据库服务
│   │   │   ├── llm_service.py  # LLM调用服务
│   │   │   └── task_service.py # 任务管理服务
│   │   ├── routers/        # API路由
│   │   │   ├── projects.py
│   │   │   └── workflow.py
│   │   ├── api/            # API工具
│   │   │   └── response.py
│   │   └── main.py         # 应用入口
│   └── requirements.txt
│
└── frontend/
    ├── lib/
    │   ├── api.ts      # API客户端
    │   ├── hooks.ts    # React Hooks
    │   ├── store.ts    # 状态管理
    │   └── utils.ts    # 工具函数
    ├── app/            # Next.js App
    ├── components/     # React组件
    └── package.json
```

## API文档

### 健康检查
```bash
GET /api/health
```

### 项目管理
```bash
GET /api/projects          # 获取项目列表
GET /api/project/{name}    # 获取项目详情
POST /api/project/create   # 创建项目
```

### 工作流
```bash
POST /api/workflow/run_all  # 执行完整工作流
GET /api/workflow/task/{id} # 获取任务状态
POST /api/workflow/step     # 执行单个步骤
```

## 部署

### Docker部署

```bash
# 构建后端镜像
cd backend
docker build -t ai-design-workflow-backend .

# 构建前端镜像
cd frontend
docker build -t ai-design-workflow-frontend .
```

### Railway + Vercel部署

1. 推送代码到GitHub
2. 在Railway部署后端（设置环境变量）
3. 在Vercel部署前端（设置NEXT_PUBLIC_API_URL）

## 监控

### 日志查看
```bash
# 后端日志
tail -f backend/logs/api_*.log
```

### 健康检查
```bash
curl http://localhost:8000/api/health
```

## 许可证

MIT
