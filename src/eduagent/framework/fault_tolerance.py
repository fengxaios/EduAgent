"""
🛡️ 容错系统 — 重试策略 + 熔断器 (v2.0)

独立于 core 层，可按需引入。
用于保护 LLM API 调用、网络请求等不稳定操作。
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Callable, Awaitable, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# 1. 重试策略
# ═══════════════════════════════════════════════════

class RetryPolicy:
    """
    指数退避重试策略

    配置:
      max_retries=3    最多重试3次
      base_delay=1.0   初始延迟1秒
      backoff=2.0      每次翻倍 → 1s, 2s, 4s
      retryable_exceptions 可重试异常白名单

    用法:
      policy = RetryPolicy(max_retries=3)
      result = await policy.execute(my_async_fn, arg1, arg2)
    """

    DEFAULT_RETRYABLE = (
        TimeoutError,
        ConnectionError,
        asyncio.TimeoutError,
    )

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 60.0,
        retryable_exceptions: tuple = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.retryable = retryable_exceptions or self.DEFAULT_RETRYABLE
        self._attempts: dict[str, int] = defaultdict(int)

    def _delay(self, attempt: int) -> float:
        """指数退避: base * backoff^(attempt-1)，上限 max_delay"""
        d = self.base_delay * (self.backoff ** (attempt - 1))
        return min(d, self.max_delay)

    async def execute(
        self, fn: Callable[..., Awaitable[Any]], *args,
        task_id: str = "", **kwargs,
    ) -> Any:
        """执行异步函数，失败时自动重试"""
        last_error = None

        for attempt in range(1, self.max_retries + 2):
            self._attempts[task_id] = attempt
            try:
                result = await fn(*args, **kwargs)
                if task_id:
                    self._attempts.pop(task_id, None)
                return result

            except Exception as e:
                last_error = e
                if not isinstance(e, self.retryable):
                    logger.warning(f"🛑 不可重试异常: {type(e).__name__} | task={task_id}")
                    raise
                if attempt > self.max_retries:
                    logger.error(f"❌ 已达最大重试次数 ({self.max_retries}) | task={task_id}")
                    raise

                delay = self._delay(attempt)
                logger.info(
                    f"🔁 重试 {attempt}/{self.max_retries} | 等待 {delay:.1f}s | task={task_id}"
                )
                await asyncio.sleep(delay)

        raise last_error


# ═══════════════════════════════════════════════════
# 2. 熔断器
# ═══════════════════════════════════════════════════

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """熔断器开启时抛出的异常"""
    pass


class CircuitBreaker:
    """
    熔断器 — 防止级联失败

    状态机:
      CLOSED ──(失败≥threshold)──▶ OPEN ──(超时后)──▶ HALF_OPEN
        ▲                                                 │
        └──────────(试探成功)─────────────────────────────┘
        │
        └──────────(试探失败)──▶ OPEN (重新计时)

    用法:
      breaker = CircuitBreaker(failure_threshold=5)

      @breaker.protect
      async def risky_api_call(): ...
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_count = 0
        self._opened_at = 0.0

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def _transition_to(self, new_state: CircuitState):
        old = self.state
        self.state = new_state
        logger.info(f"🔌 [{self.name}] {old.value} → {new_state.value}")

    def _check_timeout(self):
        if self.state == CircuitState.OPEN:
            if time.time() - self._opened_at >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                self._half_open_count = 0

    def on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_count += 1
            if self._half_open_count >= self.half_open_max:
                self._transition_to(CircuitState.CLOSED)
                self._failure_count = 0
        else:
            self._failure_count = 0

    def on_failure(self):
        self._failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
            self._opened_at = time.time()
        elif self.state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                self._opened_at = time.time()

    def protect(self, fn: Callable):
        """装饰器：用熔断器保护异步函数"""
        async def wrapper(*args, **kwargs):
            self._check_timeout()
            if self.state == CircuitState.OPEN:
                remaining = self.recovery_timeout - (time.time() - self._opened_at)
                raise CircuitBreakerOpenError(
                    f"[{self.name}] 熔断中，拒绝请求 (剩余 {remaining:.0f}s)"
                )
            try:
                result = await fn(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise
        return wrapper

    async def execute(self, fn: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """直接调用方式（非装饰器）"""
        self._check_timeout()
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"[{self.name}] 熔断中，拒绝请求")
        try:
            result = await fn(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
