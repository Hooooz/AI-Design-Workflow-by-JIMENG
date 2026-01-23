"""
LLM服务模块 - AI 设计工作流 v2

提供健壮的LLM调用，支持：
- 多模型自动降级
- 速率限制处理
- 完善的错误处理和重试
"""

import time
from typing import List, Dict, Any, Optional, Generator

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from ..core.config import config
from ..core.logger import logger


class LLMError(Exception):
    """LLM调用错误"""

    def __init__(self, message: str, recoverable: bool = True, retry_after: int = None):
        self.message = message
        self.recoverable = recoverable
        self.retry_after = retry_after
        super().__init__(message)


class LLMService:
    """
    LLM服务

    特性：
    - 同步/异步支持
    - 多模型自动降级
    - 速率限制处理
    - 详细日志
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or config.llm.api_key
        self.base_url = base_url or config.llm.base_url
        self.timeout = config.llm.timeout
        self.max_retries = config.llm.max_retries
        self.retry_delay = config.llm.retry_delay

        # 初始化同步客户端
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _should_retry(self, error: Exception, attempt: int) -> tuple[bool, int]:
        """
        判断是否应该重试

        Returns:
            (should_retry, wait_time_seconds)
        """
        error_str = str(error).lower()

        # 速率限制错误
        if any(
            kw in error_str
            for kw in ["429", "rate limit", "quota", "too many requests"]
        ):
            wait_time = self.retry_delay * (2**attempt)
            return True, min(wait_time, 60)

        # 服务器错误
        if any(
            kw in error_str
            for kw in ["500", "502", "503", "overloaded", "not available"]
        ):
            wait_time = self.retry_delay * (2**attempt)
            return True, min(wait_time, 30)

        return False, 0

    def _call_llm(
        self,
        model: str,
        messages: List[Dict[str, str]],
        extra_body: Dict[str, Any] = None,
        reasoning_effort: str = None,
    ) -> str:
        """调用LLM API"""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
        }

        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        if extra_body:
            kwargs["extra_body"] = extra_body

        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if not content:
            raise LLMError(f"模型 {model} 返回空响应", recoverable=False)

        return content

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        fallback_models: List[str] = None,
    ) -> str:
        """
        聊天补全（带自动降级）

        Args:
            messages: 消息列表
            model: 首选模型
            fallback_models: 降级模型列表
        """
        current_model = model or config.llm.default_model
        fallback_models = fallback_models or [
            "gemini-1.5-flash",
            "gpt-4o-mini",
        ]

        models_to_try = [current_model] + fallback_models
        last_error = None

        for attempt_idx, try_model in enumerate(models_to_try):
            for retry_idx in range(self.max_retries + 1):
                try:
                    # Gemini Thinking 模式配置
                    extra_body = None
                    reasoning_effort = None

                    if (
                        "gemini-2.5-flash" in try_model
                        and "flash-lite" not in try_model
                    ):
                        reasoning_effort = "none"
                        extra_body = {
                            "google": {"thinking_config": {"thinking_budget": 0}}
                        }

                    logger.info(f"调用LLM: {try_model}")
                    response = self._call_llm(
                        try_model,
                        messages,
                        extra_body=extra_body,
                        reasoning_effort=reasoning_effort,
                    )

                    logger.info(f"LLM响应成功: {try_model}")
                    return response

                except Exception as e:
                    should_retry, wait_time = self._should_retry(e, retry_idx)

                    if should_retry and retry_idx < self.max_retries:
                        logger.warning(f"LLM调用失败，等待 {wait_time}s 后重试: {e}")
                        time.sleep(wait_time)
                        continue

                    last_error = e
                    logger.warning(f"模型 {try_model} 调用失败: {e}")
                    break  # 尝试下一个模型

        raise LLMError(f"所有模型调用失败: {last_error}", recoverable=False)

    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        fallback_models: List[str] = None,
    ) -> Generator[str, None, None]:
        """
        流式聊天补完

        Yields:
            文本片段
        """
        current_model = model or config.llm.default_model
        fallback_models = fallback_models or [
            "gemini-1.5-flash",
            "gpt-4o-mini",
        ]

        models_to_try = [current_model] + fallback_models
        last_error = None

        for try_model in models_to_try:
            try:
                logger.info(f"流式调用LLM: {try_model}")

                extra_body = None
                reasoning_effort = None

                if "gemini-2.5-flash" in try_model and "flash-lite" not in try_model:
                    reasoning_effort = "none"
                    extra_body = {"google": {"thinking_config": {"thinking_budget": 0}}}

                kwargs = {
                    "model": try_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": True,
                }

                if reasoning_effort:
                    kwargs["reasoning_effort"] = reasoning_effort
                if extra_body:
                    kwargs["extra_body"] = extra_body

                response = self._client.chat.completions.create(**kwargs)

                full_response = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content

                logger.info(f"流式响应完成: {try_model}")
                return

            except Exception as e:
                last_error = e
                logger.warning(f"流式模型 {try_model} 调用失败: {e}")
                continue  # 尝试下一个模型

        raise LLMError(f"所有模型流式调用失败: {last_error}", recoverable=False)
