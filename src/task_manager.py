import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


def new_task_id() -> str:
    return uuid.uuid4().hex


def compute_dedup_key(task_type: str, payload: Dict[str, Any]) -> str:
    s = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{task_type}|{s}".encode("utf-8")).hexdigest()


def normalize_text(s: str) -> str:
    return " ".join((s or "").strip().split())


@dataclass
class TaskEntry:
    task_id: str
    task_type: str
    dedup_key: str
    status: str
    created_at: float
    updated_at: float
    result: Any = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    done: threading.Event = field(
        default_factory=threading.Event, repr=False, compare=False
    )


class TaskRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks_by_id: Dict[str, TaskEntry] = {}
        self._task_id_by_dedup_key: Dict[str, str] = {}

    def get_or_create(self, task_type: str, dedup_key: str) -> Tuple[TaskEntry, bool]:
        with self._lock:
            existing_id = self._task_id_by_dedup_key.get(dedup_key)
            if existing_id:
                entry = self._tasks_by_id.get(existing_id)
                if entry:
                    # 任务已完成，返回缓存结果
                    if entry.status == "completed":
                        return entry, False
                    # 任务失败，自动重新执行，移除旧任务
                    if entry.status == "failed":
                        self._tasks_by_id.pop(existing_id, None)
                        self._task_id_by_dedup_key.pop(dedup_key, None)
                        # fall through to create new task
                    # 任务进行中，返回现有任务（等待完成）
                    else:
                        return entry, False

            task_id = new_task_id()
            now = time.time()
            entry = TaskEntry(
                task_id=task_id,
                task_type=task_type,
                dedup_key=dedup_key,
                status="in_progress",
                created_at=now,
                updated_at=now,
            )
            self._tasks_by_id[task_id] = entry
            self._task_id_by_dedup_key[dedup_key] = task_id
            return entry, True

    def get_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        with self._lock:
            entry = self._tasks_by_id.get(task_id)
            return entry.status if entry else None

    def is_failed(self, task_id: str) -> bool:
        """检查任务是否失败"""
        return self.get_status(task_id) == "failed"

    def wait(self, task_id: str, timeout_s: float) -> Optional[TaskEntry]:
        with self._lock:
            entry = self._tasks_by_id.get(task_id)
        if not entry:
            return None
        entry.done.wait(timeout=timeout_s)
        return entry

    def complete(self, task_id: str, result: Any, duration_ms: int):
        with self._lock:
            entry = self._tasks_by_id.get(task_id)
            if not entry:
                return
            entry.status = "completed"
            entry.result = result
            entry.duration_ms = duration_ms
            entry.updated_at = time.time()
            entry.done.set()

    def fail(self, task_id: str, error_message: str):
        with self._lock:
            entry = self._tasks_by_id.get(task_id)
            if not entry:
                return
            entry.status = "failed"
            entry.error_message = error_message
            entry.updated_at = time.time()
            entry.done.set()
