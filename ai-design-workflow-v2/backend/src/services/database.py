"""
数据库服务模块 - AI 设计工作流 v2

提供健壮的Supabase数据库操作，支持：
- 自动连接重试
- 连接池管理
- 完善的错误处理
"""

import time
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from supabase import create_client, Client

from ..core.config import config
from ..core.logger import logger


class DatabaseError(Exception):
    """数据库操作错误"""

    pass


class DatabaseService:
    """
    Supabase数据库服务

    特性：
    - 懒加载连接
    - 自动重连机制
    - 连接状态监控
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._connection_retries = 3
        self._connection_delay = 1.0

    def _get_client(self) -> Client:
        """获取Supabase客户端，带重试机制"""
        if self._client is not None:
            return self._client

        db_config = config.database
        if not db_config.is_configured:
            raise DatabaseError("Supabase配置不完整")

        for attempt in range(self._connection_retries):
            try:
                self._client = create_client(
                    db_config.supabase_url, db_config.supabase_key
                )
                logger.info("Supabase连接成功")
                return self._client
            except Exception as e:
                logger.warning(f"Supabase连接尝试 {attempt + 1} 失败: {e}")
                if attempt < self._connection_retries - 1:
                    time.sleep(self._connection_delay * (attempt + 1))

        raise DatabaseError("无法连接到Supabase数据库")

    def reconnect(self) -> bool:
        """手动重连数据库"""
        try:
            self._client = None
            self._get_client()
            return True
        except Exception as e:
            logger.error(f"数据库重连失败: {e}")
            return False

    # ============ 项目操作 ============

    def get_projects(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取项目列表"""
        try:
            client = self._get_client()
            result = (
                client.table("projects")
                .select(
                    "project_name, creation_time, status, current_step, tags, model_name, brief"
                )
                .order("creation_time", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            raise DatabaseError(f"查询失败: {e}")

    def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """获取单个项目"""
        try:
            client = self._get_client()
            result = (
                client.table("projects")
                .select("*")
                .eq("project_name", project_name)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"获取项目失败: {e}")
            raise DatabaseError(f"查询失败: {e}")

    def create_project(
        self, project_name: str, brief: str, model_name: str, tags: List[str] = None
    ) -> Dict[str, Any]:
        """创建项目"""
        try:
            client = self._get_client()
            data = {
                "project_name": project_name,
                "brief": brief,
                "model_name": model_name,
                "creation_time": time.time(),
                "status": "pending",
                "current_step": "",
                "tags": tags or [],
                "content": {},
            }
            result = client.table("projects").insert(data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            raise DatabaseError(f"插入失败: {e}")

    def update_project(self, project_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """更新项目"""
        try:
            client = self._get_client()
            result = (
                client.table("projects")
                .update(kwargs)
                .eq("project_name", project_name)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"更新项目失败: {e}")
            raise DatabaseError(f"更新失败: {e}")

    def save_project_content(self, project_name: str, content: Dict[str, Any]) -> bool:
        """保存项目内容"""
        return self.update_project(project_name, content=content) is not None

    def save_project_images(self, project_name: str, images: List[str]) -> bool:
        """保存项目图片"""
        return self.update_project(project_name, images=images) is not None

    # ============ 任务状态操作 ============

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            client = self._get_client()
            result = (
                client.table("task_status").select("*").eq("task_id", task_id).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning(f"获取任务状态失败: {e}")
            return None

    def save_task_status(
        self,
        task_id: str,
        task_type: str,
        status: str,
        project_name: str = None,
        result: Dict[str, Any] = None,
        error_message: str = None,
    ) -> bool:
        """保存任务状态"""
        try:
            client = self._get_client()
            data = {
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "project_name": project_name,
                "result": result or {},
                "error_message": error_message,
                "created_at": time.time(),
                "updated_at": time.time(),
            }

            # 使用upsert进行插入或更新
            client.table("task_status").upsert(data).execute()
            return True
        except Exception as e:
            logger.warning(f"保存任务状态失败: {e}")
            return False


# 全局数据库服务实例
db_service = DatabaseService()
