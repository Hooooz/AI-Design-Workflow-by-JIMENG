# 📋 前端部署问题修复计划

## 问题
- 前端 URL: https://ai-design-workflow-by-jimeng.vercel.app → 返回空/404
- 后端 URL: https://web-production-d9bfe.up.railway.app → ✅ 正常

## 修复步骤

### 1. 检查 Next.js 构建配置
文件: `web-ui/next.config.ts`
- ✅ 已配置 rewrites
- ⚠️ 缺少输出目录配置

### 2. 修复 next.config.ts
添加必要的配置项以确保 App Router 正常工作

### 3. 配置 Vercel 环境变量
需要在 Vercel 项目中设置：
```
NEXT_PUBLIC_API_URL=https://web-production-d9bfe.up.railway.app
```

### 4. 验证部署
- 检查 Vercel 部署日志
- 测试首页访问
- 测试 API 代理

## 根本原因分析

Next.js App Router 需要正确的目录结构：
```
web-ui/
├── app/
│   ├── layout.tsx       ✅ 存在
│   ├── page.tsx        ✅ 存在
│   └── globals.css    ✅ 存在
├── next.config.ts       ✅ 存在
├── package.json
└── tsconfig.json
```

目录结构看起来是正确的，问题可能在于：
1. Vercel 构建配置
2. 环境变量设置

## 执行命令

```bash
# 部署前端到 Vercel
cd web-ui
vercel --prod
```

## 验证检查清单

- [ ] Vercel 环境变量已设置
- [ ] Vercel 构建成功
- [ ] 首页可以访问
- [ ] API 代理工作正常 (https://ai-design-workflow-by-jimeng.vercel.app/api/projects)
