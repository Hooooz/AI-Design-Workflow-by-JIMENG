"""
工作流模块测试
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保 config 模块可用
os.environ["ENV"] = "test"


class TestDesignWorkflow:
    """测试设计工作流"""

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """创建临时输出目录"""
        output_dir = tmp_path / "projects" / "test_project"
        output_dir.mkdir(parents=True)
        return str(output_dir)

    @pytest.fixture
    def mock_llm_service(self):
        """模拟 LLM 服务"""
        mock_service = Mock()
        mock_service.chat_completion.return_value = json.dumps(
            {
                "summary": "测试摘要",
                "content": "测试内容",
                "visuals": [{"concept": "概念1", "prompt": "测试提示词1"}],
            }
        )
        return mock_service

    @pytest.fixture
    def mock_image_gen(self):
        """模拟图片生成服务"""
        mock_service = Mock()
        mock_service.generate_image.return_value = None  # 不实际生成图片
        return mock_service

    def test_workflow_initialization(
        self, temp_output_dir, mock_llm_service, mock_image_gen
    ):
        """测试工作流初始化"""
        from src.main import DesignWorkflow

        with patch("src.main.LLMService", return_value=mock_llm_service):
            with patch("src.main.ImageGenService", return_value=mock_image_gen):
                workflow = DesignWorkflow(
                    output_dir=temp_output_dir,
                    custom_config={"DEFAULT_MODEL": "test-model"},
                )

        assert workflow.output_dir == temp_output_dir
        assert workflow.model == "test-model"

    def test_get_prompt_from_config(
        self, temp_output_dir, mock_llm_service, mock_image_gen
    ):
        """测试从配置获取 Prompt"""
        from src.main import DesignWorkflow

        custom_config = {
            "DEFAULT_MODEL": "test-model",
            "prompts": {"market_analyst": "自定义市场分析提示: {brief}"},
        }

        with patch("src.main.LLMService", return_value=mock_llm_service):
            with patch("src.main.ImageGenService", return_value=mock_image_gen):
                workflow = DesignWorkflow(
                    output_dir=temp_output_dir, custom_config=custom_config
                )

        prompt = workflow._get_prompt(
            "market_analyst", "默认提示: {brief}", brief="测试需求"
        )
        assert prompt == "自定义市场分析提示: 测试需求"

    def test_get_prompt_with_knowledge(
        self, temp_output_dir, mock_llm_service, mock_image_gen
    ):
        """测试带知识库的 Prompt"""
        from src.main import DesignWorkflow

        # 创建临时知识库文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("这是测试知识库内容")
            kb_path = f.name

        try:
            with patch("src.main.LLMService", return_value=mock_llm_service):
                with patch("src.main.ImageGenService", return_value=mock_image_gen):
                    with patch("os.path.exists", return_value=True):
                        workflow = DesignWorkflow(
                            output_dir=temp_output_dir, custom_config={}
                        )
                        # 重新加载知识库
                        workflow.knowledge_base = "这是测试知识库内容"

            prompt = workflow._get_prompt(
                "market_analyst", "知识: {knowledge}", brief="测试"
            )
            assert "这是测试知识库内容" in prompt
        finally:
            os.unlink(kb_path)

    def test_process_llm_json_response_valid(self):
        """测试有效的 JSON 响应处理"""
        from src.main import DesignWorkflow

        # 创建工作流实例（不需要完整初始化）
        workflow = DesignWorkflow.__new__(DesignWorkflow)
        workflow.output_dir = "/tmp/test"
        workflow.generated_images = []
        workflow.image_gen = Mock()
        workflow.image_gen.generate_image.return_value = None

        raw_response = json.dumps(
            {
                "summary": "摘要",
                "content": "完整内容",
                "visuals": [{"concept": "图1", "prompt": "提示1"}],
            }
        )

        md, prompts, data = workflow._process_llm_json_response(raw_response)

        assert "摘要" in md
        assert "完整内容" in md
        assert len(prompts) == 1
        assert data["summary"] == "摘要"

    def test_process_llm_json_response_invalid(self):
        """测试无效的 JSON 响应处理"""
        from src.main import DesignWorkflow, DesignGenerationError

        workflow = DesignWorkflow.__new__(DesignWorkflow)
        workflow.generated_images = []

        raw_response = "这不是 JSON 格式的响应"

        # 在新的实现中，无效 JSON 会抛出异常
        with pytest.raises(DesignGenerationError):
            workflow._process_llm_json_response(raw_response)

    def test_save_intermediate(self, temp_output_dir):
        """测试保存中间结果"""
        from src.main import DesignWorkflow

        workflow = DesignWorkflow.__new__(DesignWorkflow)
        workflow.output_dir = temp_output_dir

        workflow._save_intermediate("test_output.md", "# 测试内容")

        file_path = os.path.join(temp_output_dir, "test_output.md")
        assert os.path.exists(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == "# 测试内容"

    def test_save_report(self, temp_output_dir):
        """测试保存完整报告"""
        from src.main import DesignWorkflow

        workflow = DesignWorkflow.__new__(DesignWorkflow)
        workflow.output_dir = temp_output_dir

        report_path = workflow._save_report(
            "测试需求", "市场分析内容", "视觉研究内容", "设计方案内容"
        )

        assert os.path.exists(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "测试需求" in content
            assert "市场分析内容" in content
            # 检查包含报告相关的内容
            assert "市场分析" in content or "AI 设计工作流报告" in content


class TestDesignWorkflowExceptions:
    """测试工作流异常类"""

    def test_design_workflow_error(self):
        """测试基础异常类"""
        from src.main import DesignWorkflowError

        error = DesignWorkflowError("测试错误", step="test_step", recoverable=True)
        assert error.message == "测试错误"
        assert error.step == "test_step"
        assert error.recoverable is True

    def test_market_analysis_error(self):
        """测试市场分析异常"""
        from src.main import MarketAnalysisError

        error = MarketAnalysisError("市场分析失败")
        assert error.step == "market_analysis"
        assert error.recoverable is True

    def test_image_generation_error(self):
        """测试图片生成异常"""
        from src.main import ImageGenerationError

        error = ImageGenerationError("图片生成超时")
        assert error.step == "image_generation"
        assert error.recoverable is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
