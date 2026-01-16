# AI 设计工作流 - 部署与分享指南

本文档将指导你如何将这个 AI 工具开放给其他用户（同事、客户）使用。

## 方案一：局域网内部分享 (最简单)
如果你的同事和你处于同一个办公室（同一 WiFi 下）：

1. **在你电脑上启动服务**
   双击运行 `start_web.sh`，或者在终端运行：
   ```bash
   ./start_web.sh
   ```

2. **获取你的局域网 IP**
   - Mac/Linux: 终端输入 `ifconfig | grep "inet " | grep -v 127.0.0.1`
   - Windows: 终端输入 `ipconfig`

3. **分享链接**
   将你的 IP 地址加端口号发给同事，例如：
   `http://192.168.1.5:8501`

   > **注意**: 确保你的电脑防火墙允许 8501 端口的访问。

## 方案二：云端部署 (推荐)
如果你有云服务器 (阿里云/腾讯云/AWS)，可以部署在服务器上，让任何人随时访问。

1. **上传代码到服务器**
   ```bash
   scp -r AI设计工作流 root@your-server-ip:/opt/
   ```

2. **在服务器上安装环境**
   ```bash
   cd /opt/AI设计工作流
   pip install -r requirements.txt
   pip install streamlit
   # 安装 uv (用于即梦 MCP)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **后台启动服务**
   使用 `nohup` 保持后台运行：
   ```bash
   nohup streamlit run src/web_app.py --server.port 8080 &
   ```

4. **访问**
   浏览器访问 `http://your-server-ip:8080`

## 方案三：内网穿透 (临时演示)
如果你没有云服务器，但想发给外地的客户演示，可以使用 ngrok。

1. 安装 ngrok: `brew install ngrok/ngrok/ngrok`
2. 启动 Web 服务: `./start_web.sh`
3. 开启穿透: `ngrok http 8501`
4. 复制生成的 `https://xxxx.ngrok-free.app` 链接发给客户。

## ⚠️ 关于即梦绘图 (MCP) 的特别说明
由于即梦绘图服务依赖本地的 `image-gen-server` 和 `uv` 环境：
- **如果部署在云端**：你需要确保云服务器上也部署了 `image-gen-server` 文件夹，并且安装了 uv。
- **配置路径**：如果服务器上的路径不同，请在 Web 界面的侧边栏或 `CONFIG.md` 中修改 `JIMENG_SERVER_SCRIPT` 的路径。
