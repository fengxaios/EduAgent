"""
⏰ 自动化系统 — Cron调度器 + 工作流引擎 (v2.0)

独立于 core 层，可按需引入。
用于定时任务调度和多步骤工作流编排。
"""

import asyncio
import time
import heapq
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Awaitable, Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# 1. Cron 解析器
# ═══════════════════════════════════════════════════

class CronParser:
    """
    简易 Cron 表达式解析器

    支持格式:
      - 标准 cron: "minute hour day month weekday"
      - interval:   "30m", "2h", "1d"
      - one-shot:   ISO 8601 / RFC3339 timestamp
    """

    FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    @classmethod
    def parse(cls, spec: str) -> Optional[Callable[[datetime], bool]]:
        """解析调度规格，返回判断函数 fn(datetime) -> bool"""
        spec = spec.strip()

        # One-shot: ISO timestamp
        if "T" in spec and ("+" in spec or "Z" in spec or ":" in spec[10:]):
            target = datetime.fromisoformat(spec)
            return lambda now: now >= target

        # Interval: "30m", "2h", "1d"
        match = re.match(r"^(\d+)\s*(m|h|d|s)$", spec)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            interval_sec = value * multipliers[unit]
            last_fire = [0.0]

            def interval_check(now: datetime) -> bool:
                ts = now.timestamp()
                if ts - last_fire[0] >= interval_sec:
                    last_fire[0] = ts
                    return True
                return False
            return interval_check

        # 标准 cron: "min hour day month weekday"
        fields = spec.split()
        if len(fields) != 5:
            raise ValueError(f"无效的 cron 表达式: {spec}")

        field_matchers = []
        for field_str, (lo, hi) in zip(fields, cls.FIELD_RANGES):
            values = set()
            for part in field_str.split(","):
                if part == "*":
                    values.update(range(lo, hi + 1))
                elif "/" in part:
                    base, step = part.split("/")
                    base_range = range(lo, hi + 1) if base == "*" else [int(base)]
                    step = int(step)
                    for v in base_range:
                        if v % step == 0:
                            values.add(v)
                elif "-" in part:
                    start, end = map(int, part.split("-"))
                    values.update(range(start, end + 1))
                else:
                    values.add(int(part))
            field_matchers.append(values)

        def cron_check(now: datetime) -> bool:
            parts = [now.minute, now.hour, now.day, now.month, now.weekday()]
            parts[4] = (parts[4] + 1) % 7  # Python weekday → Cron weekday
            return all(p in m for p, m in zip(parts, field_matchers))

        return cron_check


# ═══════════════════════════════════════════════════
# 2. 调度器
# ═══════════════════════════════════════════════════

@dataclass(order=True)
class ScheduledJob:
    """调度任务 — 按 next_fire 排序放入优先队列"""
    next_fire: float
    name: str = field(compare=False)
    checker: Callable = field(compare=False)
    action: Callable = field(compare=False)
    timeout: float = 120.0


class CronScheduler:
    """
    定时任务调度器

    用法:
        scheduler = CronScheduler()
        scheduler.add("心跳", "30m", heartbeat_fn)
        scheduler.add("日报", "0 21 * * *", daily_report_fn)
        await scheduler.start()

    内部用最小堆管理任务队列。
    """

    def __init__(self):
        self._jobs: list[ScheduledJob] = []
        self._running = False
        self._job_results: dict[str, list] = {}

    def add(
        self, name: str, schedule: str,
        action: Callable[..., Awaitable[Any]], timeout: float = 120.0,
    ):
        """添加定时任务"""
        checker = CronParser.parse(schedule)
        if not checker:
            raise ValueError(f"无法解析调度表达式: {schedule}")

        job = ScheduledJob(
            next_fire=time.time(), name=name,
            checker=checker, action=action, timeout=timeout,
        )
        heapq.heappush(self._jobs, job)
        logger.info(f"📅 已注册: '{name}' | schedule={schedule}")

    def remove(self, name: str):
        """移除定时任务"""
        self._jobs = [j for j in self._jobs if j.name != name]
        heapq.heapify(self._jobs)

    async def start(self):
        """启动调度循环（阻塞运行）"""
        self._running = True
        logger.info("⏰ 调度器启动")

        while self._running:
            if not self._jobs:
                await asyncio.sleep(1)
                continue

            job = heapq.heappop(self._jobs)
            now = time.time()
            wait = job.next_fire - now

            if wait > 0:
                heapq.heappush(self._jobs, job)
                await asyncio.sleep(min(wait, 60))
                continue

            dt_now = datetime.fromtimestamp(now)
            if job.checker(dt_now):
                logger.info(f"🔔 触发: '{job.name}'")
                try:
                    result = await asyncio.wait_for(job.action(), timeout=job.timeout)
                    self._job_results.setdefault(job.name, []).append({
                        "ts": now, "ok": True, "result": str(result)[:200]
                    })
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ '{job.name}' 超时 ({job.timeout}s)")
                except Exception as e:
                    logger.error(f"❌ '{job.name}' 失败: {e}")

            job.next_fire = time.time() + 1
            heapq.heappush(self._jobs, job)

    def stop(self):
        self._running = False

    def status(self) -> dict:
        return {
            "running": self._running,
            "job_count": len(self._jobs),
            "jobs": [
                {"name": j.name, "next_fire": j.next_fire}
                for j in sorted(self._jobs, key=lambda x: x.next_fire)
            ],
        }


# ═══════════════════════════════════════════════════
# 3. 工作流引擎
# ═══════════════════════════════════════════════════

class WorkflowStep:
    """工作流中的一步"""

    def __init__(
        self, name: str, fn: Callable[..., Awaitable[Any]],
        depends_on: list[str] = None,
        condition: Callable[[dict], bool] = None,
        timeout: float = 300, retry: int = 0,
    ):
        self.name = name
        self.fn = fn
        self.depends_on = depends_on or []
        self.condition = condition
        self.timeout = timeout
        self.retry = retry


class WorkflowEngine:
    """
    工作流引擎

    支持:
      - DAG 依赖解析（自动并行）
      - 条件分支（condition 返回 False → 跳过）
      - 每步独立超时
      - 失败步骤自动重试

    用法:
        wf = WorkflowEngine()
        wf.add_step(WorkflowStep("fetch", fetch_fn))
        wf.add_step(WorkflowStep("process", process_fn, depends_on=["fetch"]))
        results = await wf.run(initial_context={"user_id": 123})
    """

    def __init__(self):
        self._steps: dict[str, WorkflowStep] = {}
        self._results: dict[str, Any] = {}

    def add_step(self, step: WorkflowStep):
        self._steps[step.name] = step

    def _ready_steps(self, completed: set[str], context: dict) -> list[WorkflowStep]:
        ready = []
        for step in self._steps.values():
            if step.name in completed:
                continue
            if not all(d in completed for d in step.depends_on):
                continue
            if step.condition and not step.condition(context):
                completed.add(step.name)
                logger.info(f"⏭️ 跳过: '{step.name}' (条件不满足)")
                continue
            ready.append(step)
        return ready

    async def run(self, initial_context: dict = None) -> dict[str, Any]:
        context = dict(initial_context or {})
        completed: set[str] = set()
        self._results = {}

        while len(completed) < len(self._steps):
            ready = self._ready_steps(completed, context)

            if not ready:
                remaining = set(self._steps) - completed
                blocked = [
                    s for s in remaining
                    if any(d not in completed for d in self._steps[s].depends_on)
                ]
                if blocked:
                    raise RuntimeError(f"工作流死锁: {blocked}")
                break

            logger.info(f"🚀 并行执行: {[s.name for s in ready]}")
            tasks = []
            for step in ready:
                task = asyncio.wait_for(
                    self._execute_step(step, context), timeout=step.timeout
                )
                tasks.append((step, task))

            results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)

            for (step, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    if step.retry > 0:
                        for attempt in range(step.retry):
                            try:
                                result = await asyncio.wait_for(
                                    step.fn(context), timeout=step.timeout
                                )
                                break
                            except Exception:
                                if attempt == step.retry - 1:
                                    raise
                    else:
                        raise result

                completed.add(step.name)
                self._results[step.name] = result
                context[step.name] = result

        return self._results

    async def _execute_step(self, step: WorkflowStep, context: dict) -> Any:
        logger.info(f"  ▶ {step.name}")
        result = await step.fn(context)
        logger.info(f"  ✓ {step.name} 完成")
        return result
