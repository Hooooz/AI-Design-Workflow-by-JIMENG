"""
即梦图片生成服务 - HTTP API 版本
用于 Railway 部署
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志 - 先配置，确保能输出
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logger.info("🚀 启动中...")

# 配置
JIMENG_API_TOKEN = os.getenv("JIMENG_API_TOKEN", "881abd7d55218d875202db7510cdafbb")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "/tmp/images")

# 确保输出目录存在
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 延迟导入，即梦模块
_jimeng_generate = None
_import_error = None

try:
    proxy_path = str(Path(__file__).parent / "proxy")
    if proxy_path not in sys.path:
        sys.path.insert(0, proxy_path)
    from proxy.jimeng import generate_images as _jimeng_generate

    logger.info("✅ 即梦模块导入成功")
except Exception as e:
    _import_error = str(e)
    logger.error(f"❌ 即梦模块导入失败: {e}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Image Gen Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str
    file_name: str
    save_folder: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    image_path: Optional[str] = None
    message: str = ""


@app.get("/health")
async def health():
    """健康检查 - 始终返回 OK"""
    return {"status": "ok", "import_error": _import_error}


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "image-gen-server",
        "status": "running",
        "import_error": _import_error,
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest):
    """生成图片"""
    if _import_error:
        return GenerateResponse(success=False, message=f"模块未加载: {_import_error}")

    if not _jimeng_generate:
        return GenerateResponse(success=False, message="生成函数未初始化")

    try:
        logger.info(f"收到生成请求: {req.prompt[:50]}...")

        save_folder = req.save_folder or OUTPUT_FOLDER
        os.makedirs(save_folder, exist_ok=True)

        result = _jimeng_generate(
            prompt=req.prompt,
            file_name=req.file_name,
            save_folder=save_folder,
            token=JIMENG_API_TOKEN,
        )

        if result and os.path.exists(result):
            logger.info(f"图片生成成功: {result}")
            return GenerateResponse(success=True, image_path=result, message="生成成功")
        else:
            return GenerateResponse(success=False, message="生成失败，未返回图片路径")

    except Exception as e:
        logger.error(f"生成失败: {e}")
        return GenerateResponse(success=False, message=str(e))


if __name__ == "__main__":
    logger.info(f"启动服务，端口: {os.getenv('PORT', '8080')}")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
