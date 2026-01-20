# 安全指南

本文档描述了 AI 设计工作流的安全最佳实践和注意事项。

## 🚨 重要安全声明

### API Key 安全

**绝对禁止**将 API Key 硬编码在代码中！

```python
# ❌ 错误做法
OPENAI_API_KEY = "sk-xxx..."

# ✅ 正确做法
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("API Key 未配置")
```

### 环境变量配置

1. **开发环境**: 使用 `.env` 文件（已加入 .gitignore）
2. **生产环境**: 使用系统环境变量或密钥管理服务

```bash
# 设置环境变量
export OPENAI_API_KEY="sk-your-api-key"
export ENV="production"
```

## 🛡️ 安全措施

### 1. 输入验证

系统对所有用户输入进行严格验证：

- **项目名称**: 只允许字母、数字、空格、下划线、连字符
- **设计需求**: 限制长度，检查恶意代码
- **模型名称**: 白名单机制

```python
from security import validate_project_name, validate_brief_content

# 验证项目名称
validated_name = validate_project_name(user_input)

# 验证需求内容
validated_brief = validate_brief_content(user_brief)
```

### 2. 路径安全

防止路径遍历攻击：

```python
from security import sanitize_path

# 安全路径拼接
safe_path = sanitize_path(base_dir, user_path)
```

### 3. 日志安全

日志不记录敏感信息：

```python
# ✅ 正确做法 - 只记录元数据
log_entry = {
    "timestamp": ...,
    "model": model,
    "message_count": len(messages),
    "content_length": content_length,
}

# ❌ 错误做法 - 记录完整消息
log_entry = {
    "messages": messages,  # 可能包含敏感数据
    "response": response,
}
```

### 4. 速率限制

API 端点有速率限制，防止滥用：

- 默认: 100 请求/分钟
- 可通过 `API_RATE_LIMIT` 环境变量配置

## 🔐 生产环境部署建议

### 1. 环境配置

```bash
# 设置严格的环境变量
export ENV=production
export OPENAI_API_KEY="sk-your-secure-api-key"
export ALLOWED_ORIGINS="https://yourdomain.com"
export API_RATE_LIMIT="50/minute"
```

### 2. CORS 配置

**开发环境**:
```python
ALLOWED_ORIGINS = ["*"]  # 不推荐用于生产
```

**生产环境**:
```python
ALLOWED_ORIGINS = ["https://yourdomain.com", "https://admin.yourdomain.com"]
```

### 3. 网络安全

- 使用 HTTPS
- 部署在专用网络或使用 VPN
- 考虑使用 WAF (Web Application Firewall)

### 4. 监控和日志

- 启用访问日志
- 监控异常请求
- 设置告警阈值

## 🐛 常见安全问题

### Q: 发现 API Key 泄露怎么办？

1. **立即撤销**该 API Key
2. 生成新的 API Key
3. 更新所有环境变量
4. 检查日志，确认是否有滥用

### Q: 如何报告安全漏洞？

请通过以下方式报告：
- GitHub Issues (标记为 security)
- 邮件: security@example.com

## 📚 参考资源

- [OWASP Web Application Security](https://owasp.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/advanced/security/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
