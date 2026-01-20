# Figma 集成 - 设计令牌同步

本功能支持将代码中的设计令牌（Design Tokens）同步到 Figma 本地样式。

## 功能特性

- 从 CSS 文件解析颜色变量（支持 Hex 和 OKLCH 格式）
- 生成可直接在 Figma 中运行的插件脚本
- 自动创建/更新 Figma 本地样式（Paint Styles）
- 可视化颜色预览面板

## 快速开始

### 1. 配置环境变量

在 `.env` 文件中添加 Figma 认证信息：

```bash
# Figma Access Token - 从 https://www.figma.com/developers/api#access-tokens 获取
FIGMA_ACCESS_TOKEN=your-figma-personal-access-token

# Figma 文件 Key - 从 Figma 文件 URL 中提取
# 例如: https://www.figma.com/file/{FILE_KEY}/...
FIGMA_FILE_KEY=SxLfBs9WqtldB48fZkKOA4
```

### 2. 启动后端服务

```bash
cd AI设计工作流
python3 -m src.main
```

### 3. 使用同步功能

#### 方法一：使用 Web 界面

访问 Figma 同步页面：`http://localhost:8000/figma-sync.html`

1. 点击"生成 Figma 插件脚本"按钮
2. 复制生成的脚本代码
3. 在 Figma 中运行插件

#### 方法二：使用 API

```bash
# 生成脚本
curl -X POST http://localhost:8000/api/figma/sync-from-css

# 获取文件信息
curl http://localhost:8000/api/figma/file-info

# 获取现有样式
curl http://localhost:8000/api/figma/styles
```

#### 方法三：使用命令行脚本

```bash
python3 scripts/generate_figma_sync_script.py
```

脚本将生成 `scripts/figma_sync.js` 文件。

### 4. 在 Figma 中运行

1. 打开 Figma
2. 进入 `Plugins → Development → New Plugin`
3. 粘贴生成的脚本代码
4. 点击运行按钮
5. 脚本将自动创建样式并生成预览页面

## API 参考

### POST /api/figma/generate-plugin-script

生成 Figma 插件脚本。

**请求体：**
```json
{
  "colors": {
    "primary": "#000000",
    "secondary": "#ffffff"
  },
  "typography": {},
  "file_name": "Design System"
}
```

**响应：**
```json
{
  "status": "success",
  "script": "// Figma Plugin Script...",
  "instructions": "Copy this script...",
  "colors_count": 2
}
```

### POST /api/figma/sync-from-css

从 CSS 文件解析变量并生成插件脚本。

**响应：**
```json
{
  "status": "success",
  "script": "// Figma Plugin Script...",
  "colors": {
    "primary": "oklch(0.205 0 0)"
  }
}
```

### GET /api/figma/file-info

获取 Figma 文件信息。

### GET /api/figma/styles

获取 Figma 文件中的现有样式。

## 注意事项

1. **API 限制**：Figma REST API 无法直接创建样式，需要通过插件脚本实现
2. **颜色格式**：支持 Hex (`#ffffff`) 和 OKLCH (`oklch(0.5 0.1 200)`) 格式
3. **字体加载**：脚本会自动加载 Inter 字体，如需其他字体请修改脚本
4. **样式命名**：颜色变量名会自动转换为 Figma 样式名（`--primary` → `Design Tokens/primary`）

## 手动运行 Figma 插件

如果需要手动运行已生成的脚本：

```bash
# 查看生成的脚本
cat scripts/figma_sync.js
```

复制内容后在 Figma 中粘贴运行。
