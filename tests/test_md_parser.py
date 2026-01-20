"""
Markdown 解析器测试
"""

import pytest
import sys
import os
import tempfile

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMdParser:
    """测试 Markdown 解析器"""

    @pytest.fixture
    def sample_request_md(self):
        """示例 REQUEST.md 内容"""
        return """
**项目名称**: 测试项目

## 2. 详细需求描述
> 这是一个测试需求

设计一款创新产品，需要考虑用户体验和市场趋势。
"""

    @pytest.fixture
    def sample_config_md(self):
        """示例 CONFIG.md 内容"""
        return """# 系统配置

```yaml
OPENAI_API_KEY: "sk-test-key"
DEFAULT_MODEL: "gemini-2.5-flash"
```

### Agent: 市场分析师 (market_analyst)
```text
你是一个市场分析师，分析用户需求：{brief}
```
"""

    def test_parse_request_md(self, sample_request_md):
        """测试解析 REQUEST.md"""
        from src.md_parser import parse_request_md

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(sample_request_md)
            f.flush()

            try:
                result = parse_request_md(f.name)

                assert result["project_name"] == "测试项目"
                # 验证需求描述存在
                assert len(result["description"]) > 0
            finally:
                os.unlink(f.name)

    def test_parse_request_md_missing_project_name(self):
        """测试缺少项目名称的情况"""
        from src.md_parser import parse_request_md

        content = """
## 2. 详细需求描述
> 需求描述

内容
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            try:
                result = parse_request_md(f.name)

                assert result["project_name"] == "untitled_project"
            finally:
                os.unlink(f.name)

    def test_parse_config_md(self, sample_config_md):
        """测试解析 CONFIG.md"""
        from src.md_parser import parse_config_md

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_config_md)
            f.flush()

            try:
                result = parse_config_md(f.name)

                assert "OPENAI_API_KEY" in result
                assert result["OPENAI_API_KEY"] == "sk-test-key"
                assert "DEFAULT_MODEL" in result
                assert result["DEFAULT_MODEL"] == "gemini-2.5-flash"
                assert "prompts" in result
                assert "market_analyst" in result["prompts"]
            finally:
                os.unlink(f.name)

    def test_parse_config_md_with_special_chars(self):
        """测试包含特殊字符的配置"""
        from src.md_parser import parse_config_md

        content = """# 配置

```yaml
OPENAI_BASE_URL: "http://localhost:8000/v1"
```

### Agent: 产品设计师 (product_designer)
```text
请设计产品：{brief}
考虑因素：{knowledge}
```
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            try:
                result = parse_config_md(f.name)

                assert result["OPENAI_BASE_URL"] == "http://localhost:8000/v1"
                assert "product_designer" in result["prompts"]
            finally:
                os.unlink(f.name)

    def test_parse_config_md_multiple_agents(self):
        """测试多个 Agent 的配置"""
        from src.md_parser import parse_config_md

        content = """# 配置

```yaml
DEFAULT_MODEL: "test-model"
```

### Agent 1: 市场分析师 (market_analyst)
```text
市场分析 {brief}
```

### Agent 2: 视觉研究员 (visual_researcher)
```text
视觉研究 {brief} {market_analysis}
```

### Agent: 产品设计师 (product_designer)
```text
设计方案 {brief} {market_analysis} {visual_research}
```
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            try:
                result = parse_config_md(f.name)

                assert "market_analyst" in result["prompts"]
                assert "visual_researcher" in result["prompts"]
                assert "product_designer" in result["prompts"]
            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
