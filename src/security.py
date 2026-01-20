import os
import re
from typing import Optional
from fastapi import HTTPException
from pydantic import field_validator, Field
import pydantic


class SafeProjectName(str):
    """
    自定义类型：安全的项目名称，支持 Unicode（中文）字符
    绕过 FastAPI 默认的 Path 参数验证问题
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not isinstance(v, str):
            raise HTTPException(status_code=400, detail="项目名称必须是字符串")

        # 验证并返回
        return validate_project_name(v)


class _SafeProjectNamePydantic(pydantic.StringConstraints):
    pass


def validate_project_name(project_name: str) -> str:
    """
    验证项目名称的合法性，防止路径遍历攻击
    """
    if not project_name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    # 检查长度
    if len(project_name) < 1 or len(project_name) > 100:
        raise HTTPException(status_code=400, detail="项目名称长度必须在1-100个字符之间")

    # 允许 Unicode 字符（支持中文、日文等），只禁止危险字符
    # 使用 re.UNICODE 标志确保 \w 匹配 Unicode 字符
    if not re.match(r"^[\w\s\-\u4e00-\u9fff]+$", project_name, re.UNICODE):
        # 检查是否只包含允许的字符（更宽松的检查）
        if re.match(
            r"^[\w\s\-\.\,\:\;\!\?\@\u4e00-\u9fff]+$", project_name, re.UNICODE
        ):
            # 如果包含一些额外字符但没有危险字符，仍然允许
            pass
        else:
            raise HTTPException(
                status_code=400,
                detail="项目名称只能包含字母、数字、空格、下划线和连字符和中文",
            )

    # 检查是否包含危险字符
    dangerous_patterns = ["..", "../", "\\", "$", "`", "|", ";"]
    for pattern in dangerous_patterns:
        if pattern in project_name:
            raise HTTPException(
                status_code=400, detail=f"项目名称包含非法字符: {pattern}"
            )

    return project_name.strip()


def sanitize_path(base_dir: str, path: str) -> str:
    """
    安全路径拼接，防止路径遍历攻击
    """
    # 规范化路径
    full_path = os.path.normpath(os.path.join(base_dir, path))

    # 确保路径在 base_dir 内部
    if not full_path.startswith(os.path.normpath(base_dir)):
        raise HTTPException(status_code=400, detail="非法路径访问")

    # 检查路径是否存在
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件或目录不存在")

    return full_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符
    """
    if not filename:
        return ""

    # 移除路径分隔符
    filename = os.path.basename(filename)

    # 只保留安全字符
    safe_chars = re.compile(r"[^a-zA-Z0-9_\-\.]")
    filename = safe_chars.sub("_", filename)

    # 限制长度
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[: max_length - len(ext)] + ext

    return filename


def validate_brief_content(brief: str) -> str:
    """
    验证设计需求内容
    """
    if not brief or not brief.strip():
        raise HTTPException(status_code=400, detail="设计需求不能为空")

    max_length = 10000  # 10KB
    if len(brief) > max_length:
        raise HTTPException(
            status_code=400, detail=f"设计需求长度不能超过{max_length}字符"
        )

    # 检查是否包含潜在的注入攻击
    dangerous_patterns = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"exec\s*\(",
        r"system\s*\(",
        r"subprocess",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, brief, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="输入内容包含非法字符或模式")

    return brief.strip()


def validate_model_name(model_name: str) -> Optional[str]:
    """
    验证模型名称
    """
    allowed_models = [
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]

    # 如果为空，返回默认模型
    if not model_name:
        return "gemini-2.5-flash"

    # 验证是否在允许列表中
    if model_name not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模型: {model_name}。允许的模型: {', '.join(allowed_models)}",
        )

    return model_name
