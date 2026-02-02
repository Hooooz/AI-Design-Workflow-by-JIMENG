#!/bin/bash

# 阿里云一键部署 Jimeng-Dify-Service 脚本
# 使用方法：在服务器上运行 bash deploy_aliyun.sh

set -e

echo "=== 开始部署 Jimeng-Dify-Service ==="

# 0. 环境检查
if [[ "$(uname)" == "Darwin" ]]; then
    echo "❌ 错误：检测到您正在 macOS (本地电脑) 上运行此脚本。"
    echo "请务必先 SSH 连接到阿里云服务器，然后再运行此脚本。"
    echo "连接命令: ssh root@8.130.32.43"
    exit 1
fi

# 1. 检查并安装 Docker
if ! command -v docker &> /dev/null; then
    echo "正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
else
    echo "Docker 已安装"
fi

# 2. 检查并安装 Docker Compose
if ! docker compose version &> /dev/null; then
    echo "正在安装 Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
fi

# 3. 检查并安装 Git
if ! command -v git &> /dev/null; then
    echo "正在安装 Git..."
    apt-get update && apt-get install -y git || yum install -y git
fi

# 4. 创建工作目录
WORK_DIR="/opt/jimeng-dify"
mkdir -p $WORK_DIR
cd $WORK_DIR

# 4. 拉取代码
echo "正在拉取最新代码..."
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/Hooooz/Dify-config---JIMENG.git .
fi

# 5. 进入部署目录
cd _railway_deploy_repo

# 6. 设置环境变量（交互式输入或使用默认）
read -p "请输入您的即梦 API Token (JIMENG_API_TOKEN): " API_TOKEN
if [ -z "$API_TOKEN" ]; then
    echo "错误：必须提供 API Token"
    exit 1
fi

export JIMENG_API_TOKEN=$API_TOKEN
export PUBLIC_BASE_URL="http://$(curl -s ifconfig.me):8080"

# 更新 docker-compose.yml 中的环境变量（如果需要持久化，这里简单使用环境变量传给 docker compose）
echo "JIMENG_API_TOKEN=$JIMENG_API_TOKEN" > .env
echo "PUBLIC_BASE_URL=$PUBLIC_BASE_URL" >> .env
echo "PORT=8080" >> .env
echo "ALLOW_ORIGINS=*" >> .env

# 7. 启动服务
echo "正在启动服务..."
docker compose up -d --build

echo "=== 部署完成！ ==="
echo "服务地址: $PUBLIC_BASE_URL"
echo "健康检查: $PUBLIC_BASE_URL/health"
echo "请确保阿里云安全组已开放 8080 端口 (TCP)"
