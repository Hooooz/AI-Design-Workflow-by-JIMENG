# 生产环境配置指南

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│ Vercel (前端)                                               │
│ 域名: https://ai-design-workflow-by-jimeng.vercel.app      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Railway (后端 API)                                          │
│ 域名: https://web-production-d9bfe.up.railway.app          │
│ - 处理 LLM 调用 (Gemini)                                    │
│ - 调用即梦 API 生成图片                                      │
│ - 保存图片到文件系统                                         │
│ - 更新数据库                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 即梦 API                                                    │
│ - 图片生成服务                                               │
│ Token: 881abd7d55218d875202db7510cdafbb                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Supabase (数据库)                                           │
│ - 存储项目元数据                                             │
│ - 存储文档内容                                               │
└─────────────────────────────────────────────────────────────┘
```

## Railway 后端环境变量配置

在 Railway 后端服务的 Settings → Variables 中配置：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ENV` | `production` | 设为 production |
| `OPENAI_API_KEY` | `sk-your-key` | OpenAI API Key (用于代理) |
| `OPENAI_BASE_URL` | `http://47.89.249.90:8000/openai/v1` | LLM 代理地址 |
| `JIMENG_API_TOKEN` | `881abd7d55218d875202db7510cdafbb` | ✅ **即梦 Token** |
| `SUPABASE_URL` | `https://yojpsrakcqkyeaoxqlxg.supabase.co` | Supabase URL |
| `SUPABASE_KEY` | `eyJhbGci...` | Supabase Service Role Key |

**⚠️ 重要：删除以下错误配置**
- ~~`IMAGE_GEN_SERVER_URL=881abd7d55218d875202db7510cdafbb`~~ ❌ 删除！

## Vercel 前端环境变量配置

在 Vercel 项目的 Settings → Environment Variables 中配置：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://web-production-d9bfe.up.railway.app` | ✅ 后端地址 |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://yojpsrakcqkyeaoxqlxg.supabase.co` | Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_...` | Supabase Anon Key |

## 目录结构

```
src/
├── api.py           # FastAPI 服务
├── main.py          # 设计工作流
├── image_gen.py     # 即梦图片生成 ⭐ 已修改为直接调用
├── jimeng/          # 即梦模块 ⭐ 新增 - 确保生产环境可用
│   ├── __init__.py
│   ├── images.py
│   ├── core.py
│   ├── utils.py
│   ├── chat.py
│   └── exceptions.py
├── config.py        # 配置
└── ...
```

## 部署步骤

### 1. 提交代码更改
```bash
git add -A
git commit -m "fix: 支持生产环境直接调用即梦 API"
git push
```

### 2. 部署到 Railway
```bash
# 如果使用 Railway CLI
railway up

# 或在 Railway Dashboard 中自动部署
```

### 3. 更新环境变量
在 Railway Dashboard 中：
- 确保 `JIMENG_API_TOKEN` 已设置
- 删除错误的 `IMAGE_GEN_SERVER_URL`

### 4. 测试
1. 打开 https://ai-design-workflow-by-jimeng.vercel.app
2. 创建一个新项目
3. 运行到图片生成步骤
4. 检查是否成功生成图片

## 故障排除

### 问题: 图片生成失败

**检查步骤:**
1. 查看 Railway 后端日志
2. 确认 `JIMENG_API_TOKEN` 是否正确
3. 确认即梦账户是否有积分

### 问题: 提示 "图片服务未配置"

**原因:** `JIMENG_API_TOKEN` 未设置或即梦模块未找到

**解决:**
```bash
# 在 Railway 后端检查环境变量
railway variables

# 确认 src/jimeng 目录存在
ls -la src/jimeng/
```

### 问题: 前端显示 "API Error"

**原因:** `NEXT_PUBLIC_API_URL` 配置错误

**解决:** 确保指向正确的 Railway 后端地址

## 依赖说明

项目依赖已包含在 `requirements.txt` 中：
- `requests` - HTTP 请求
- `brotli` - 即梦 API 响应解压
- `supabase` - 数据库连接
- `openai` - LLM 调用

即梦模块没有额外依赖，直接使用 `requests`。
