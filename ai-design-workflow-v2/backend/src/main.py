"""
主应用入口 - AI 设计工作流 v2
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import config
from .core.logger import logger
from .api.response import APIError, APIResponse
from .routers import projects, workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info(f"启动AI设计工作流服务 (环境: {config.env})")
    logger.info(
        f"Supabase配置: {'已配置' if config.database.is_configured else '未配置'}"
    )

    yield

    # 关闭
    logger.info("关闭AI设计工作流服务")


app = FastAPI(
    title="AI Design Workflow API v2",
    description="AI设计工作流 - 稳定版",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(projects.router)
app.include_router(workflow.router)


# 全局异常处理
@app.exception_handler(APIError)
async def api_error_handler(request, exc: APIError):
    return exc.to_response()


# 根路径
@app.get("/")
async def root():
    return APIResponse(
        success=True,
        data={
            "name": "AI Design Workflow API v2",
            "version": "2.0.0",
            "status": "running",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug,
    )
