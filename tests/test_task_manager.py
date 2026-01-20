"""
任务管理器测试
"""

import pytest
import sys
import os
import time
import threading

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTaskManager:
    """测试任务管理器"""

    @pytest.fixture
    def task_registry(self):
        """创建任务注册表"""
        from src.task_manager import TaskRegistry

        return TaskRegistry()

    def test_new_task_id(self):
        """测试生成任务 ID"""
        from src.task_manager import new_task_id

        task_id1 = new_task_id()
        task_id2 = new_task_id()

        # 应该生成不同且有效的 UUID
        assert len(task_id1) == 32  # SHA256 hex length
        assert task_id1 != task_id2

    def test_compute_dedup_key(self):
        """测试计算去重键"""
        from src.task_manager import compute_dedup_key

        payload = {"key": "value", "number": 123}
        key1 = compute_dedup_key("test_task", payload)
        key2 = compute_dedup_key("test_task", payload)

        # 相同输入应该产生相同输出
        assert key1 == key2

        # 不同任务类型应该产生不同输出
        key3 = compute_dedup_key("different_task", payload)
        assert key1 != key3

    def test_normalize_text(self):
        """测试文本规范化"""
        from src.task_manager import normalize_text

        assert normalize_text("  hello   world  ") == "hello world"
        assert normalize_text("") == ""
        assert normalize_text(None) == ""
        assert normalize_text("normal") == "normal"

    def test_task_registry_creation(self, task_registry):
        """测试任务注册表创建"""
        assert isinstance(task_registry._tasks_by_id, dict)
        assert isinstance(task_registry._task_id_by_dedup_key, dict)
        assert len(task_registry._tasks_by_id) == 0

    def test_get_or_create_new_task(self, task_registry):
        """测试创建新任务"""
        dedup_key = "test_dedup_key_123"
        entry, created = task_registry.get_or_create("test_type", dedup_key)

        assert created is True
        assert entry is not None
        assert entry.task_type == "test_type"
        assert entry.dedup_key == dedup_key
        assert entry.status == "in_progress"

    def test_get_or_create_existing_task(self, task_registry):
        """测试获取已存在的任务"""
        dedup_key = "test_dedup_key_456"

        # 创建任务
        entry1, created1 = task_registry.get_or_create("test_type", dedup_key)
        assert created1 is True

        # 再次获取（应该返回相同的）
        entry2, created2 = task_registry.get_or_create("test_type", dedup_key)
        assert created2 is False
        assert entry1.task_id == entry2.task_id

    def test_complete_task(self, task_registry):
        """测试完成任务"""
        dedup_key = "test_dedup_key_789"
        entry, _ = task_registry.get_or_create("test_type", dedup_key)

        # 完成任务
        task_registry.complete(entry.task_id, result={"done": True}, duration_ms=100)

        assert entry.status == "completed"
        assert entry.result == {"done": True}
        assert entry.duration_ms == 100

    def test_fail_task(self, task_registry):
        """测试任务失败"""
        dedup_key = "test_dedup_key_000"
        entry, _ = task_registry.get_or_create("test_type", dedup_key)

        # 标记失败
        task_registry.fail(entry.task_id, error_message="Something went wrong")

        assert entry.status == "failed"
        assert entry.error_message == "Something went wrong"

    def test_wait_for_completion(self, task_registry):
        """测试等待任务完成"""
        dedup_key = "test_dedup_key_wait"
        entry, _ = task_registry.get_or_create("test_type", dedup_key)

        # 在后台完成
        def complete_after_delay():
            time.sleep(0.1)
            task_registry.complete(entry.task_id, result="done", duration_ms=50)

        thread = threading.Thread(target=complete_after_delay)
        thread.start()

        # 等待完成
        result = task_registry.wait(entry.task_id, timeout_s=1)

        assert result is not None
        assert result.status == "completed"
        assert result.result == "done"

    def test_wait_timeout(self, task_registry):
        """测试等待超时"""
        dedup_key = "test_dedup_key_timeout"
        entry, _ = task_registry.get_or_create("test_type", dedup_key)

        # 不完成任务，直接等待（应该超时）
        result = task_registry.wait(entry.task_id, timeout_s=0.1)

        assert result is not None
        assert result.status == "in_progress"  # 仍然是进行中

    def test_wait_nonexistent_task(self, task_registry):
        """测试等待不存在的任务"""
        result = task_registry.wait("nonexistent_id", timeout_s=0.1)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
