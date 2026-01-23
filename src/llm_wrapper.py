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

    def chat_completion(self, messages: List[Dict[str, str]], model: str = None) -> str:
        """
        调用 LLM 生成回复，支持自动模型降级 (Failover)。
        策略：优先尝试指定模型，失败后按优先级列表尝试其他模型。
        """
        start_time = time.time()
        if not self.client:
            error_msg = f"LLM Client not initialized. API_KEY: {'Set' if self.api_key else 'Missing'}, BASE_URL: {self.base_url}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # 确定模型尝试序列
        # 1. 默认情况：使用 config 中的优先级列表
        # 2. 指定情况：优先尝试指定模型，失败后尝试列表中剩余的模型
        candidate_models = list(config.MODEL_PRIORITY_LIST)
        requested_model = model or config.DEFAULT_MODEL

        # 如果请求的模型不在列表中，把它加到最前面
        if requested_model not in candidate_models:
            candidate_models.insert(0, requested_model)
        else:
            # 如果在列表中，确保它排在第一个，并保持列表其余部分的相对顺序
            candidate_models.remove(requested_model)
            candidate_models.insert(0, requested_model)

        last_error = None

        for current_model in candidate_models:
            try:
                # 内部函数：执行单个模型的调用（含参数重试逻辑）
                def _call(
                    extra_body: Dict[str, Any] | None, reasoning_effort: str | None
                ):
                    kwargs = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": 0.7,
                        "timeout": 60.0,
                    }
                    if reasoning_effort:
                        kwargs["reasoning_effort"] = reasoning_effort
                    if extra_body:
                        kwargs["extra_body"] = extra_body
                    return self.client.chat.completions.create(**kwargs)

                # Gemini Thinking 参数配置
                disable_gemini_thinking = (
                    os.getenv("DISABLE_GEMINI_THINKING", "1") != "0"
                )
                reasoning_effort = None
                extra_body = None
                if (
                    disable_gemini_thinking
                    and ("gemini-2.5-flash" in current_model)
                    and ("flash-lite" not in current_model)
                ):
                    reasoning_effort = "none"
                    extra_body = {"google": {"thinking_config": {"thinking_budget": 0}}}

                # 单个模型的重试循环（处理参数错误等）
                max_retries = 1
                retry_count = 0

                while retry_count <= max_retries:
                    try:
                        print(f"📡 Calling LLM ({current_model})...")
                        response = _call(
                            extra_body=extra_body, reasoning_effort=reasoning_effort
                        )

                        raw_content = response.choices[0].message.content
                        if not raw_content:
                            raise ValueError(
                                f"Model {current_model} returned empty response."
                            )

                        result = str(raw_content).strip()

                        if len(result) < 5:
                            raise ValueError(
                                f"Model {current_model} returned too short response."
                            )

                        duration = time.time() - start_time
                        self._log_call(current_model, messages, result, duration)
                        print(
                            f"✅ LLM Response received from {current_model} ({duration:.2f}s)"
                        )
                        return result

                    except Exception as e:
                        # 参数错误重试逻辑
                        if (
                            extra_body is not None or reasoning_effort is not None
                        ) and retry_count == 0:
                            retry_count += 1
                            print(
                                f"⚠️ [{current_model}] 参数不兼容，移除 extra_body 重试..."
                            )
                            reasoning_effort = None
                            extra_body = None
                            continue
                        raise e  # 抛出给外层处理（进行模型切换）

            except Exception as e:
                last_error = e
                duration = time.time() - start_time
                error_msg = str(e).lower()

                # 判断是否值得切换模型
                # 增加了 "empty/invalid response" 的检测
                should_failover = any(
                    code in error_msg
                    for code in [
                        "404",
                        "429",
                        "500",
                        "not found",
                        "rate limit",
                        "overloaded",
                        "empty/invalid",
                    ]
                )

                if should_failover:
                    print(
                        f"⚠️ Model {current_model} failed: {str(e)[:100]}... -> Trying next model"
                    )
                    continue  # Try next model

                # 如果是其他严重错误（如认证失败），直接终止
                print(f"❌ Unrecoverable error on {current_model}: {e}")
                raise e

        # 所有模型都尝试失败
        print("❌ All candidate models failed.")
        raise last_error

    def chat_completion_stream(self, messages: List[Dict[str, str]], model: str = None):
        """
        调用 LLM 生成流式回复，支持自动模型降级 (Failover)。
        """
        start_time = time.time()
        if not self.client:
            raise ValueError("LLM Client not initialized")

        # 确定模型尝试序列 (同上)
        candidate_models = list(config.MODEL_PRIORITY_LIST)
        requested_model = model or config.DEFAULT_MODEL
        if requested_model not in candidate_models:
            candidate_models.insert(0, requested_model)
        else:
            candidate_models.remove(requested_model)
            candidate_models.insert(0, requested_model)

        last_error = None

        for current_model in candidate_models:
            try:

                def _call_stream(extra_body, reasoning_effort):
                    kwargs = {
                        "model": current_model,
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

                # Gemini 参数配置
                reasoning_effort = None
                extra_body = None
                # ... (同样的参数配置逻辑) ...

                # 执行流式调用
                print(f"📡 Calling LLM Stream ({current_model})...")
                full_response = ""

                # 注意：流式调用在这里只是建立连接，如果在迭代过程中报错，很难在这里捕获并切换模型
                # 所以我们主要捕获建立连接时的错误
                stream = _call_stream(extra_body, reasoning_effort)

                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content

                # 成功完成
                duration = time.time() - start_time
                self._log_call(current_model, messages, full_response, duration)
                print(f"✅ LLM Stream completed from {current_model} ({duration:.2f}s)")
                return

            except Exception as e:
                last_error = e
                print(f"⚠️ Model {current_model} stream failed: {str(e)[:100]}")
                # 简单判断是否继续尝试下一个模型
                continue

        print("❌ All candidate models failed for stream.")
        raise last_error
