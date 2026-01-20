"""
安全模块测试
"""

import pytest
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.security import (
    validate_project_name,
    sanitize_filename,
    validate_brief_content,
    validate_model_name,
)


class TestValidateProjectName:
    """测试项目名称验证"""

    def test_valid_names(self):
        """测试有效的项目名称"""
        assert validate_project_name("My_Project") == "My_Project"
        assert validate_project_name("project-123") == "project-123"
        assert validate_project_name("New Project") == "New Project"

    def test_empty_name(self):
        """测试空名称"""
        with pytest.raises(Exception):
            validate_project_name("")

    def test_invalid_characters(self):
        """测试包含非法字符"""
        with pytest.raises(Exception):
            validate_project_name("../etc/passwd")
        with pytest.raises(Exception):
            validate_project_name("project$name")
        with pytest.raises(Exception):
            validate_project_name("project|name")

    def test_dangerous_patterns(self):
        """测试危险模式"""
        with pytest.raises(Exception):
            validate_project_name("project..")
        with pytest.raises(Exception):
            validate_project_name("project/../etc")


class TestSanitizeFilename:
    """测试文件名清理"""

    def test_safe_filename(self):
        """测试安全文件名"""
        assert sanitize_filename("image.jpg") == "image.jpg"
        assert sanitize_filename("my_document_v2.pdf") == "my_document_v2.pdf"

    def test_unsafe_filename(self):
        """测试危险文件名清理"""
        # 危险字符会被清理或移除
        result1 = sanitize_filename("../../../etc/passwd")
        assert result1 == "passwd" or result1 == ""  # 可能被 os.path.basename 处理

    def test_empty_filename(self):
        """测试空文件名"""
        assert sanitize_filename("") == ""


class TestValidateBriefContent:
    """测试需求内容验证"""

    def test_valid_brief(self):
        """测试有效需求"""
        valid_brief = "设计一款智能家居产品，要求具有现代感的外观。"
        assert validate_brief_content(valid_brief) == valid_brief

    def test_empty_brief(self):
        """测试空需求"""
        with pytest.raises(Exception):
            validate_brief_content("")

    def test_too_long_brief(self):
        """测试过长需求"""
        long_brief = "a" * 10001
        with pytest.raises(Exception):
            validate_brief_content(long_brief)

    def test_malicious_content(self):
        """测试恶意内容"""
        with pytest.raises(Exception):
            validate_brief_content("<script>alert('xss')</script>")
        with pytest.raises(Exception):
            validate_brief_content("javascript:alert('xss')")
        with pytest.raises(Exception):
            validate_brief_content("exec('rm -rf /')")


class TestValidateModelName:
    """测试模型名称验证"""

    def test_valid_models(self):
        """测试有效模型名称"""
        assert validate_model_name("gemini-2.0-flash-exp") == "gemini-2.0-flash-exp"
        assert validate_model_name("gemini-1.5-pro") == "gemini-1.5-pro"
        assert validate_model_name("") == "gemini-2.5-flash"  # 默认值

    def test_invalid_model(self):
        """测试无效模型名称"""
        with pytest.raises(Exception):
            validate_model_name("invalid-model")
        with pytest.raises(Exception):
            validate_model_name("gpt-4")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
