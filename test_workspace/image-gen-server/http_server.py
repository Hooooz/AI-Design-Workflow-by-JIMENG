"""
即梦图片生成服务 - HTTP API 版本
用于 Railway 部署
"""

import os
import sys
import json
import time
import base64
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# 添加代理路径
sys.path.insert(0, str(Path(__file__).parent / "proxy"))
from proxy.jimeng import generate_images as jimeng_generate

# 配置
JIMENG_API_TOKEN = os.getenv("JIMENG_API_TOKEN", "881abd7d55218d875202db7510cdafbb")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "/tmp/images")

# 确保输出目录存在
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest):
    """生成图片"""
    try:
        logger.info(f"收到生成请求: {req.prompt[:50]}...")

        save_folder = req.save_folder or OUTPUT_FOLDER
        os.makedirs(save_folder, exist_ok=True)

        # 调用即梦生成
        result = jimeng_generate(
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


@app.post("/generate-sync")
async def generate_image_sync(
    prompt: str, file_name: str, save_folder: str = OUTPUT_FOLDER
):
    """同步生成图片（兼容旧接口）"""
    try:
        os.makedirs(save_folder, exist_ok=True)

        result = jimeng_generate(
            prompt=prompt,
            file_name=file_name,
            save_folder=save_folder,
            token=JIMENG_API_TOKEN,
        )

        if result and os.path.exists(result):
            # 返回 base64 图片
            with open(result, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode()

            return {
                "success": True,
                "image_path": result,
                "image_base64": img_base64,
                "message": "生成成功",
            }
        else:
            return {"success": False, "message": "生成失败"}

    except Exception as e:
        logger.error(f"生成失败: {e}")
        return {"success": False, "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
