import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Any

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import config


class RateLimitError(Exception):
    """速率限制错误，需要切换模型"""

    def __init__(self, message="Rate limit exceeded", retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class LLMService:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_BASE_URL
        self.client = None

        # Initialize logs directory
        self.log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
        )
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.log_file = os.path.join(self.log_dir, "llm_calls.jsonl")

        # 只要有 API Key 就尝试初始化，不再检查前缀
        if OpenAI and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")


class LLMService:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_BASE_URL
        self.client = None

        # 速率限制跟踪
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 最小请求间隔（秒）

        # Initialize logs directory
        self.log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
        )
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.log_file = os.path.join(self.log_dir, "llm_calls.jsonl")

        # 只要有 API Key 就尝试初始化，不再检查前缀
        if OpenAI and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")

    def _check_rate_limit(self):
        """检查并实施速率限制"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """检查是否为速率限制错误 (429)"""
        error_str = str(error).lower()
        return (
            "429" in error_str
            or "rate limit" in error_str
            or "quota" in error_str
            or "exceeded" in error_str
            or "too many requests" in error_str
        )

    def _should_retry_with_backoff(
        self, error: Exception, retry_count: int, max_retries: int = 3
    ) -> tuple:
        """
        判断是否应该退避重试，返回 (should_retry, wait_time)
        """
        if not self._is_rate_limit_error(error):
            return False, 0

        if retry_count >= max_retries:
            return False, 0

        # 指数退避：2^retry_count 秒
        wait_time = min(2**retry_count, 60)  # 最多等待60秒
        return True, wait_time

    def _log_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: str,
        duration: float,
        status: str = "success",
    ):
        """
        记录模型调用日志（不包含敏感信息）
        """
        # 只记录消息数量和角色，不记录内容
        safe_messages = [{"role": msg["role"]} for msg in messages]

        # 计算消息摘要长度
        content_length = sum(len(msg.get("content", "")) for msg in messages)
        response_length = len(response) if response else 0

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "message_count": len(messages),
            "content_length": content_length,
            "response_length": response_length,
            "duration_ms": int(duration * 1000),
            "status": status,
        }

        # 只在开发环境记录响应内容摘要
        if config.ENV == "development" and status == "success":
            log_entry["response_preview"] = (
                response[:200] + "..." if len(response) > 200 else response
            )

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Failed to write LLM log: {e}")

    def chat_completion(
        self, messages: List[Dict[str, str]], model: str = config.DEFAULT_MODEL
    ) -> str:
        """
        调用 LLM 生成回复，遇到 429 速率限制时抛出 RateLimitError 以触发模型切换。
        """
        start_time = time.time()
        if not self.client:
            error_msg = f"LLM Client not initialized. API_KEY: {'Set' if self.api_key else 'Missing'}, BASE_URL: {self.base_url}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        def _call(extra_body: Dict[str, Any] | None, reasoning_effort: str | None):
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "timeout": 60.0,
            }
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            if extra_body:
                kwargs["extra_body"] = extra_body
            return self.client.chat.completions.create(**kwargs)

        disable_gemini_thinking = os.getenv("DISABLE_GEMINI_THINKING", "1") != "0"
        reasoning_effort = None
        extra_body = None
        if (
            disable_gemini_thinking
            and ("gemini-2.5-flash" in (model or ""))
            and ("flash-lite" not in (model or ""))
        ):
            reasoning_effort = "none"
            extra_body = {"google": {"thinking_config": {"thinking_budget": 0}}}

        max_retries = (
            1  # 遇到 429 只重试 1 次，然后就抛出 RateLimitError 让上层切换模型
        )
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                print(f"📡 Calling LLM ({model})...")
                response = _call(
                    extra_body=extra_body, reasoning_effort=reasoning_effort
                )
                result = response.choices[0].message.content
                duration = time.time() - start_time
                self._log_call(model, messages, result, duration)
                print(f"✅ LLM Response received ({duration:.2f}s)")
                return result

            except Exception as e:
                last_error = e

                # 如果是 429 速率限制，抛出 RateLimitError 让上层切换模型
                if self._is_rate_limit_error(e):
                    duration = time.time() - start_time
                    print(f"⚠️ 速率限制触发 (429)，需要切换模型: {str(e)[:80]}")
                    raise RateLimitError(str(e))

                # 处理其他错误，尝试无额外参数重试
                if (
                    extra_body is not None or reasoning_effort is not None
                ) and retry_count == 0:
                    retry_count += 1
                    print(f"⚠️ 重试移除 extra_body/reasoning_effort 参数...")
                    reasoning_effort = None
                    extra_body = None
                    continue

                # 其他错误直接抛出
                duration = time.time() - start_time
                error_detail = f"API Error: {str(e)}"
                print(f"❌ {error_detail}")
                self._log_call(model, messages, error_detail, duration, status="error")
                raise e

        # 理论上不会到这里
        duration = time.time() - start_time
        self._log_call(model, messages, str(last_error), duration, status="error")
        raise last_error

    def chat_completion_stream(
        self, messages: List[Dict[str, str]], model: str = config.DEFAULT_MODEL
    ):
        """
        调用 LLM 生成流式回复，遇到 429 速率限制时抛出 RateLimitError 以触发模型切换。
        """
        start_time = time.time()
        if not self.client:
            error_msg = f"LLM Client not initialized. API_KEY: {'Set' if self.api_key else 'Missing'}, BASE_URL: {self.base_url}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        def _call_stream(
            extra_body: Dict[str, Any] | None, reasoning_effort: str | None
        ):
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "timeout": 60.0,
                "stream": True,
            }
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            if extra_body:
                kwargs["extra_body"] = extra_body
            return self.client.chat.completions.create(**kwargs)

        disable_gemini_thinking = os.getenv("DISABLE_GEMINI_THINKING", "1") != "0"
        reasoning_effort = None
        extra_body = None
        if (
            disable_gemini_thinking
            and ("gemini-2.5-flash" in (model or ""))
            and ("flash-lite" not in (model or ""))
        ):
            reasoning_effort = "none"
            extra_body = {"google": {"thinking_config": {"thinking_budget": 0}}}

        max_retries = (
            1  # 遇到 429 只重试 1 次，然后就抛出 RateLimitError 让上层切换模型
        )
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                full_response = ""
                print(f"📡 Calling LLM Stream ({model})...")
                stream = _call_stream(
                    extra_body=extra_body, reasoning_effort=reasoning_effort
                )

                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content

                duration = time.time() - start_time
                self._log_call(model, messages, full_response, duration)
                print(f"✅ LLM Stream completed ({duration:.2f}s)")
                return

            except Exception as e:
                last_error = e

                # 如果是 429 速率限制，抛出 RateLimitError 让上层切换模型
                if self._is_rate_limit_error(e):
                    duration = time.time() - start_time
                    print(f"⚠️ 速率限制触发 (429)，需要切换模型: {str(e)[:80]}")
                    raise RateLimitError(str(e))

                # 处理其他错误，尝试无额外参数重试
                if (
                    extra_body is not None or reasoning_effort is not None
                ) and retry_count == 0:
                    retry_count += 1
                    print(f"⚠️ 重试移除 extra_body/reasoning_effort 参数...")
                    reasoning_effort = None
                    extra_body = None
                    continue

                # 其他错误直接抛出
                duration = time.time() - start_time
                error_detail = f"API Stream Error: {str(e)}"
                print(f"❌ {error_detail}")
                self._log_call(model, messages, error_detail, duration, status="error")
                raise e

        # 理论上不会到这里
        duration = time.time() - start_time
        self._log_call(model, messages, str(last_error), duration, status="error")
        raise last_error
