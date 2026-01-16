#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🌐 正在准备公网访问环境..."

# 2. 检查 Web 服务是否运行
if ! pgrep -f "streamlit run" > /dev/null; then
    echo "🚀 正在启动本地 Web 服务..."
    # 使用后台运行，并将日志输出到 web.log
    nohup ./start_web.sh > web.log 2>&1 &
    
    # 等待服务端口 8501 开启
    echo "⏳ 正在等待服务启动..."
    for i in {1..30}; do
        if lsof -i :8501 > /dev/null; then
            echo "✅ 服务已就绪 (Port 8501)"
            break
        fi
        sleep 1
        echo -n "."
    done
else
    echo "✅ 本地 Web 服务已在运行"
fi

echo "--------------------------------------------------"
echo "🌍 正在尝试多种公网方案..."
echo "--------------------------------------------------"

# 方案 1: Pinggy.io (推荐，无需安装，无验证)
# 使用 Port 443 绕过防火墙，StrictHostKeyChecking=no 防止交互
# 使用 +tcp 模式避免密码提示 (Pinggy HTTP 模式无需密码，但有时 SSH 会询问)
# 注意：Pinggy 免费版有时会弹出 TUI，我们尝试 suppressed output
echo "✅ 尝试启动 Pinggy.io (Port 443)..."
echo "👉 请复制下方的 'http://....pinggy.link' 链接"
ssh -p 443 -R0:localhost:8501 -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o PasswordAuthentication=no a.pinggy.io 2>/dev/null &
PID=$!
sleep 5
if kill -0 $PID 2>/dev/null; then
    # 保持前台运行
    wait $PID
    exit 0
else
    echo "⚠️ Pinggy.io 连接失败 (可能需要密码或被阻断)，尝试 Cloudflare..."
fi

# 方案 2: Cloudflare Tunnel (最稳定，无验证)
# 检查 cloudflared 是否存在，不存在尝试下载
if [ ! -f "./cloudflared" ]; then
    echo "⬇️ 正在下载 cloudflared..."
    # 使用 tarball 下载方式，因为直接 binary 可能 404
    curl -L --output cloudflared-darwin-arm64.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz
    tar -xzf cloudflared-darwin-arm64.tgz
    chmod +x cloudflared
    rm cloudflared-darwin-arm64.tgz
fi

if [ -f "./cloudflared" ]; then
    echo "✅ 启动 Cloudflare Tunnel..."
    echo "👉 请复制下方 'https://....trycloudflare.com' 的链接"
    ./cloudflared tunnel --url http://localhost:8501
    exit 0
fi

# 方案 3: LocalTunnel (备选，有验证)
if command -v npm &> /dev/null; then
    echo "✅ 检测到 Node.js，正在启动 LocalTunnel..."
    echo "👉 请复制下方的 'your url is: ...' 链接"
    echo "⚠️ 注意：首次访问可能需要输入 IP 地址 (localtunnel 保护机制)"
    # 使用 -y 自动确认安装
    npx -y localtunnel --port 8501
    exit 0
fi

# 方案 3: ngrok (需要 Token)
echo "⚠️ 未检测到 Node.js，尝试使用 ngrok..."
./ngrok http 8501 --config "$HOME/.ngrok2/ngrok.yml"
