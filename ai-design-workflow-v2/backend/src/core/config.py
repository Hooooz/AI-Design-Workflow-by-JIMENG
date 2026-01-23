"""
统一配置模块 - AI 设计工作流 v2

提供健壮的配置管理，支持：
- 环境变量覆盖
- 配置验证
- 开发/生产环境自动切换
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class DatabaseConfig:
    """数据库配置"""

    supabase_url: str = ""
    supabase_key: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


@dataclass
class LLMConfig:
    """LLM服务配置"""

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gemini-2.5-flash"
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class APIConfig:
    """API服务配置"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = field(default_factory=lambda: ["*"])
    rate_limit: str = "100/minute"


@dataclass
class ImageGenConfig:
    """图片生成服务配置"""

    jimeng_script_path: str = ""
    max_concurrent: int = 3


class Config:
    """
    统一配置管理器

    配置优先级（从高到低）：
    1. 环境变量
    2. .env 文件
    3. 代码默认值
    """

    def __init__(self):
        self._env = os.getenv("ENV", "development")
        self._db = DatabaseConfig()
        self._llm = LLMConfig()
        self._api = APIConfig()
        self._image_gen = ImageGenConfig()
        self._load_from_env()
        self._validate()

    def _load_from_env(self):
        """从环境变量加载配置"""
        # 数据库配置
        self._db.supabase_url = os.getenv("SUPABASE_URL", "")
        self._db.supabase_key = os.getenv("SUPABASE_KEY", "")

        # LLM配置
        self._llm.api_key = os.getenv("OPENAI_API_KEY", "")
        self._llm.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # 如果环境变量中没有API Key，使用开发环境兜底Key
        if not self._llm.api_key:
            if self._env == "production":
                # 生产环境严格要求配置
                self._llm.api_key = ""
            else:
                # 开发环境使用兜底Key
                self._llm.api_key = os.getenv(
                    "OPENAI_API_KEY_FALLBACK",
                    "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6",
                )

        # 图片生成配置
        if self._env == "production":
            self._image_gen.jimeng_script_path = str(
                Path.cwd() / "test_workspace/image-gen-server/server.py"
            )
        else:
            self._image_gen.jimeng_script_path = os.getenv(
                "JIMENG_SERVER_SCRIPT",
                "/Users/huangchuhao/Downloads/AI 工具/Cursor 代码库/Howie AI 工作室/彩友乐 AI 提效/AI设计工作流/test_workspace/image-gen-server/server.py",
            )

        # API配置
        self._api.port = int(os.getenv("PORT", "8000"))
        self._api.debug = self._env == "development"
        self._api.cors_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

        # 图片生成并发数
        self._image_gen.max_concurrent = int(os.getenv("MAX_CONCURRENT_IMAGES", "3"))

    def _validate(self):
        """验证配置有效性"""
        errors = []

        if not self._llm.api_key:
            errors.append("OPENAI_API_KEY 未设置")

        if self._env == "production":
            if not self._db.supabase_url:
                errors.append("生产环境必须设置 SUPABASE_URL")
            if not self._db.supabase_key:
                errors.append("生产环境必须设置 SUPABASE_KEY")

        if errors:
            raise ValueError(f"配置验证失败: {', '.join(errors)}")

    @property
    def env(self) -> str:
        return self._env

    @property
    def is_production(self) -> bool:
        return self._env == "production"

    @property
    def database(self) -> DatabaseConfig:
        return self._db

    @property
    def llm(self) -> LLMConfig:
        return self._llm

    @property
    def api(self) -> APIConfig:
        return self._api

    @property
    def image_gen(self) -> ImageGenConfig:
        return self._image_gen


# 全局配置实例
config = Config()
