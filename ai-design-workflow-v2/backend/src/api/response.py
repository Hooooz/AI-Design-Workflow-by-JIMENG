"""
API响应模块 - AI 设计工作流 v2

提供统一的API响应格式和错误处理
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class APIResponse:
    """统一API响应格式"""

    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class APIError(Exception):
    """API错误"""

    def __init__(
        self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)

    def to_response(self) -> APIResponse:
        return APIResponse(
            success=False,
            error=self.message,
        )


class NotFoundError(APIError):
    """资源不存在"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=404,
            code="NOT_FOUND",
        )


class ValidationError(APIError):
    """参数验证错误"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            code="VALIDATION_ERROR",
        )


class ServiceUnavailableError(APIError):
    """服务不可用"""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            status_code=503,
            code="SERVICE_UNAVAILABLE",
        )


def success_response(data: Any) -> APIResponse:
    """成功响应"""
    return APIResponse(success=True, data=data)


def error_response(message: str, status_code: int = 500) -> APIResponse:
    """错误响应"""
    return APIResponse(success=False, error=message)
