#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查是否安装了 uv
if ! command -v uv &> /dev/null; then
    echo "⚠️ 未检测到 uv，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# 检查依赖
echo "📦 正在检查 Python 依赖..."
pip install -r requirements.txt
pip install streamlit

# 配置 Streamlit 避免首次运行弹窗
mkdir -p ~/.streamlit
if [ ! -f ~/.streamlit/credentials.toml ]; then
    echo '[general]
email = ""
' > ~/.streamlit/credentials.toml
fi
if [ ! -f ~/.streamlit/config.toml ]; then
    echo '[server]
headless = true
' > ~/.streamlit/config.toml
fi

# 启动 Web 服务
echo "🚀 正在启动 AI 设计工作台..."
echo "👉 请在浏览器中访问显示的 Local URL"
echo "--------------------------------------------------"

# 添加用户 Python bin 目录到 PATH
export PATH="$HOME/Library/Python/3.13/bin:$PATH"

# 尝试查找 streamlit 路径
if command -v streamlit &> /dev/null; then
    STREAMLIT_CMD="streamlit"
elif [ -f "$HOME/Library/Python/3.13/bin/streamlit" ]; then
    STREAMLIT_CMD="$HOME/Library/Python/3.13/bin/streamlit"
else
    # 尝试使用 python -m streamlit
    STREAMLIT_CMD="python3 -m streamlit"
fi

$STREAMLIT_CMD run src/web_app.py --server.port 8501 --server.address 0.0.0.0
