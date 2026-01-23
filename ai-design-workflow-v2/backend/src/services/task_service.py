"""
任务服务模块 - AI 设计工作流 v2

提供持久化的任务状态管理，支持：
- 数据库持久化
- 自动重试
- 状态追踪
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .database import db_service, DatabaseError


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskEntry:
    """任务条目"""

    task_id: str
    task_type: str
    dedup_key: str
    status: TaskStatus
    project_name: Optional[str]
    created_at: float
    updated_at: float
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class TaskService:
    """
    任务服务

    特性：
    - 数据库持久化（服务重启不丢失）
    - 任务去重
    - 自动重试
    """

    def __init__(self):
        self._cache: Dict[str, TaskEntry] = {}

    def _compute_dedup_key(self, task_type: str, payload: Dict[str, Any]) -> str:
        """计算任务去重键"""
        s = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(f"{task_type}|{s}".encode("utf-8")).hexdigest()

    def _new_task_id(self) -> str:
        """生成新任务ID"""
        return uuid.uuid4().hex

    def get_or_create(
        self, task_type: str, payload: Dict[str, Any], project_name: str = None
    ) -> tuple[TaskEntry, bool]:
        """
        获取现有任务或创建新任务

        Returns:
            (TaskEntry, is_new): 任务条目和是否是新任务
        """
        dedup_key = self._compute_dedup_key(task_type, payload)

        # 先从数据库查找
        try:
            db_result = db_service.get_task_status_by_dedup(dedup_key)
            if db_result:
                entry = TaskEntry(
                    task_id=db_result["task_id"],
                    task_type=db_result["task_type"],
                    dedup_key=dedup_key,
                    status=TaskStatus(db_result["status"]),
                    project_name=db_result.get("project_name"),
                    created_at=db_result["created_at"],
                    updated_at=db_result["updated_at"],
                    result=db_result.get("result", {}),
                    error_message=db_result.get("error_message"),
                    duration_ms=db_result.get("duration_ms"),
                )

                # 如果任务已完成，直接返回缓存结果
                if entry.status == TaskStatus.COMPLETED:
                    return entry, False

                # 如果任务失败，允许重试
                if entry.status == TaskStatus.FAILED:
                    pass  # 继续创建新任务

                # 任务进行中
                return entry, False
        except DatabaseError:
            pass

        # 创建新任务
        task_id = self._new_task_id()
        now = time.time()
        entry = TaskEntry(
            task_id=task_id,
            task_type=task_type,
            dedup_key=dedup_key,
            status=TaskStatus.IN_PROGRESS,
            project_name=project_name,
            created_at=now,
            updated_at=now,
        )

        # 保存到数据库
        db_service.save_task_status(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.IN_PROGRESS.value,
            project_name=project_name,
        )

        self._cache[task_id] = entry
        return entry, True

    def complete(self, task_id: str, result: Dict[str, Any], duration_ms: int):
        """标记任务完成"""
        now = time.time()

        # 更新缓存
        if task_id in self._cache:
            entry = self._cache[task_id]
            entry.status = TaskStatus.COMPLETED
            entry.result = result
            entry.duration_ms = duration_ms
            entry.updated_at = now

        # 更新数据库
        db_service.save_task_status(
            task_id=task_id,
            task_type="",  # 不更新
            status=TaskStatus.COMPLETED.value,
            result=result,
            duration_ms=duration_ms,
        )

    def fail(self, task_id: str, error_message: str):
        """标记任务失败"""
        now = time.time()

        # 更新缓存
        if task_id in self._cache:
            entry = self._cache[task_id]
            entry.status = TaskStatus.FAILED
            entry.error_message = error_message
            entry.updated_at = now

        # 更新数据库
        db_service.save_task_status(
            task_id=task_id,
            task_type="",
            status=TaskStatus.FAILED.value,
            error_message=error_message,
        )

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        # 先查缓存
        if task_id in self._cache:
            return self._cache[task_id].status

        # 查数据库
        try:
            result = db_service.get_task_status(task_id)
            if result:
                return TaskStatus(result["status"])
        except DatabaseError:
            pass

        return None


# 全局任务服务实例
task_service = TaskService()
