"""
Pytest 配置文件
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# 设置测试环境变量
os.environ["ENV"] = "test"
os.environ["OPENAI_API_KEY"] = "test-api-key"


def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 按文件分组测试
    items.sort(key=lambda item: (item.fspath, item.name))
