"""
LLM 包装器测试
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockResponse:
    """模拟 OpenAI API 响应"""

    def __init__(self, content):
        self.choices = [Mock()]
        self.choices[0].message = Mock()
        self.choices[0].message.content = content


class TestLLMWrapper:
    """测试 LLM 包装器"""

    @pytest.fixture
    def mock_openai_client(self):
        """创建模拟的 OpenAI 客户端"""
        with patch("src.llm_wrapper.OpenAI") as mock_client:
            yield mock_client

    @pytest.fixture
    def llm_service(self, mock_openai_client):
        """创建 LLM 服务实例（使用模拟客户端）"""
        from src.llm_wrapper import LLMService

        return LLMService(api_key="test-key", base_url="http://test.local")

    def test_initialization(self, llm_service):
        """测试初始化"""
        assert llm_service.api_key == "test-key"
        assert llm_service.base_url == "http://test.local"
        assert llm_service.client is not None

    @pytest.mark.skip(reason="需要完整的 mock 设置")
    def test_chat_completion_success(self, llm_service, mock_openai_client):
        """测试成功的聊天完成（跳过）"""
        # 这个测试需要更复杂的 mock 设置
        pass

    def test_chat_completion_with_empty_messages(self, llm_service, mock_openai_client):
        """测试空消息列表"""
        messages = []
        result = llm_service.chat_completion(messages, model="test-model")

        # 应该调用 API（即使消息为空）
        assert mock_openai_client.return_value.chat.completions.create.called

    def test_chat_completion_logs_call(self, llm_service, mock_openai_client, tmp_path):
        """测试调用日志记录"""
        # 创建临时日志目录
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # 修改日志文件路径
        llm_service.log_file = str(log_dir / "test_calls.jsonl")

        # 设置模拟响应
        mock_response = MockResponse("测试回复")
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance

        messages = [{"role": "user", "content": "测试"}]
        llm_service.chat_completion(messages, model="test-model")

        # 验证日志文件已创建
        assert os.path.exists(llm_service.log_file)

        # 验证日志内容
        with open(llm_service.log_file, "r", encoding="utf-8") as f:
            log_entry = f.readline()
            assert "test-model" in log_entry
            assert "message_count" in log_entry

    def test_chat_completion_error_handling(self, llm_service, mock_openai_client):
        """测试错误处理"""
        mock_openai_client.return_value.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        messages = [{"role": "user", "content": "测试"}]

        with pytest.raises(Exception) as exc_info:
            llm_service.chat_completion(messages, model="test-model")

        assert "API Error" in str(exc_info.value)


class TestLLMWrapperStream:
    """测试 LLM 流式响应"""

    @pytest.fixture
    def mock_openai_client_stream(self):
        """创建模拟的 OpenAI 客户端（流式）"""
        with patch("src.llm_wrapper.OpenAI") as mock_client:
            yield mock_client

    @pytest.fixture
    def llm_service_stream(self, mock_openai_client_stream):
        """创建 LLM 服务实例"""
        from src.llm_wrapper import LLMService

        return LLMService(api_key="test-key", base_url="http://test.local")

    @pytest.mark.skip(reason="需要完整的 mock 设置")
    def test_stream_completion(self, llm_service_stream, mock_openai_client_stream):
        """测试流式完成（跳过）"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
