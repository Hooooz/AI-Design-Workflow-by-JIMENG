import os

# 环境配置: 'production' 或 'development'
ENV = os.getenv("ENV", "development")

# 配置 API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6") 
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://47.89.249.90:8000/openai/v1")

# 模型配置
DEFAULT_MODEL = "gemini-2.5-flash"

# 输出目录
OUTPUT_DIR = "output"

# 即梦绘图服务脚本路径
if ENV == "production":
    # 生产环境使用相对路径或容器内路径
    JIMENG_SERVER_SCRIPT = os.path.join(os.getcwd(), "test_workspace/image-gen-server/server.py")
else:
    # 开发环境使用本地绝对路径
    JIMENG_SERVER_SCRIPT = os.getenv("JIMENG_SERVER_SCRIPT", "/Users/huangchuhao/Downloads/AI 工具/Cursor 代码库/Howie AI 工作室/彩友乐 AI 提效/AI设计工作流/test_workspace/image-gen-server/server.py")
