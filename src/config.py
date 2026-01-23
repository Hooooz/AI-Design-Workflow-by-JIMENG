import os

# 环境配置: 'production' 或 'development'
ENV = os.getenv("ENV", "development")

# 配置 API Key
# 生产环境: 必须通过环境变量设置
# 开发环境: 优先使用环境变量，如果没有则使用开发 Key（仅用于本地调试）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    if ENV == "production":
        # 生产环境严格要求配置，但用户要求暂时放开使用测试 Key
        print("⚠️ 警告: 生产环境使用了硬编码的测试 Key (用户要求)")
        OPENAI_API_KEY = "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6"
    else:
        # 开发环境使用兜底 Key（仅限本地调试）
        OPENAI_API_KEY = os.getenv(
            "OPENAI_API_KEY_FALLBACK",
            "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6",
        )
        print("⚠️ 警告: 使用了开发环境兜底 API Key，生产环境请设置 OPENAI_API_KEY")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://47.89.249.90:8000/openai/v1")

# 模型配置
DEFAULT_MODEL = "gemini-2.0-flash-exp"

# 输出目录
OUTPUT_DIR = "output"

# 即梦绘图服务脚本路径
if ENV == "production":
    # 生产环境使用相对路径或容器内路径
    JIMENG_SERVER_SCRIPT = os.path.join(
        os.getcwd(), "test_workspace/image-gen-server/server.py"
    )
else:
    # 开发环境使用本地绝对路径，从环境变量读取或使用默认值
    JIMENG_SERVER_SCRIPT = os.getenv(
        "JIMENG_SERVER_SCRIPT",
        "/Users/huangchuhao/Downloads/AI 工具/Cursor 代码库/Howie AI 工作室/彩友乐 AI 提效/AI设计工作流/test_workspace/image-gen-server/server.py",
    )

# Supabase 数据库配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL:
    print("⚠️ 警告: SUPABASE_URL 未设置，数据库功能将不可用")

# 安全配置
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
MAX_CONCURRENT_IMAGES = int(os.getenv("MAX_CONCURRENT_IMAGES", "3"))
API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "100/minute")

# 开发环境兜底配置（仅本地调试用）
# 使用环境变量可以覆盖默认值
_OPENAI_API_KEY_FALLBACK = os.getenv(
    "OPENAI_API_KEY_FALLBACK", "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6"
)
