"""
🤖 AgentRunner — 隔离执行器 (v2.0)

与 core.agent.Agent 互补：
- core.agent.Agent: Plan→Execute→Reflect 三阶段循环（单Agent认知模型）
- framework.agent_runner.AgentRunner: Snapshot→Execute→Verify→Rollback（多Agent执行容器）

使用方式：把你的 core.agent.Agent 实例包装到 AgentRunner 中，
即可获得快照回滚 + 超时控制 + 并行执行能力。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from abc import ABC, abstractmethod
import asyncio
import time
import copy
import logging

from .protocol import Task, Result, TaskStatus, AcceptanceCriteria

logger = logging.getLogger(__name__)


# ── 快照管理器 ────────────────────────────────────

@dataclass
class Snapshot:
    """Agent 执行前的完整状态快照"""
    task_id: str
    state: dict
    timestamp: float = field(default_factory=time.time)


class SnapshotManager:
    """管理 Agent 的快照创建、存储、回滚和清理"""

    def __init__(self, max_snapshots: int = 50):
        self._snapshots: dict[str, Snapshot] = {}
        self._max = max_snapshots

    def capture(self, task_id: str, state: dict) -> Snapshot:
        """创建快照"""
        snap = Snapshot(task_id=task_id, state=copy.deepcopy(state))
        self._snapshots[task_id] = snap
        if len(self._snapshots) > self._max:
            oldest = min(self._snapshots.keys(),
                        key=lambda k: self._snapshots[k].timestamp)
            del self._snapshots[oldest]
        return snap

    def restore(self, task_id: str) -> Optional[dict]:
        """恢复到快照状态"""
        snap = self._snapshots.get(task_id)
        return copy.deepcopy(snap.state) if snap else None

    def discard(self, task_id: str):
        """成功执行后清理快照"""
        self._snapshots.pop(task_id, None)

    def cleanup_expired(self, max_age_seconds: float = 3600):
        """清理过期快照"""
        now = time.time()
        expired = [
            tid for tid, snap in self._snapshots.items()
            if now - snap.timestamp > max_age_seconds
        ]
        for tid in expired:
            del self._snapshots[tid]


# ── AgentRunner 基类 ─────────────────────────────

class AgentRunner(ABC):
    """
    Agent 执行器基类 — 所有 v2.0 Agent 的父类

    子类只需要实现 _execute() 方法，框架自动处理：
      - 快照创建与回滚
      - 超时控制
      - 验收清单校验
      - 指标收集

    也可以作为 v1.0 core.agent.Agent 的包装器使用（见 AgentRunnerAdapter）。
    """

    def __init__(self, name: str, agent_type: str, timeout: int = 300):
        self.name = name
        self.agent_type = agent_type
        self.default_timeout = timeout
        self._snapshots = SnapshotManager()
        self._state: dict = {}

    # ── 子类必须实现 ──────────────────────────────

    @abstractmethod
    async def _execute(self, task: Task) -> dict:
        """
        子类实现具体业务逻辑
        返回 dict → 自动封装为 Result.data
        抛出异常 → 自动触发回滚
        """
        ...

    # ── 子类可选覆盖 ──────────────────────────────

    def _validate(self, result_data: dict, criteria: AcceptanceCriteria) -> bool:
        """子类可覆盖验收逻辑，默认总是通过"""
        return True

    def _on_rollback(self, task: Task, error: Exception) -> None:
        """回滚时的自定义清理逻辑"""
        pass

    # ── 框架自动处理的执行流程 ─────────────────────

    async def execute(self, task: Task) -> Result:
        """
        完整执行流程：
        Snapshot → _execute → _validate → Commit / Rollback
        """
        result = Result(task_id=task.id, started_at=time.time())
        timeout = task.timeout or self.default_timeout

        # 1. 创建快照
        self._snapshots.capture(task.id, dict(self._state))
        logger.info(f"[{self.name}] 📸 快照已创建 | task={task.id}")

        try:
            # 2. 带超时的隔离执行
            result_data = await asyncio.wait_for(
                self._execute(task), timeout=timeout
            )
            result.data = result_data

            # 3. 验收清单校验
            passed = self._validate(result_data, task.criteria)
            if not passed:
                raise ValueError(f"验收失败: {task.criteria.checks}")

            # 4. 成功 → 提交
            result.status = TaskStatus.SUCCESS
            self._snapshots.discard(task.id)
            logger.info(f"[{self.name}] ✅ 执行成功 | task={task.id}")

        except asyncio.TimeoutError:
            result.status = TaskStatus.TIMEOUT
            result.errors.append(f"超时 ({timeout}s)")
            restored = self._snapshots.restore(task.id)
            if restored:
                self._state = restored
            logger.warning(f"[{self.name}] ⏰ 超时 | task={task.id}")

        except Exception as e:
            # 5. 失败 → 回滚到快照
            result.status = TaskStatus.FAILED
            result.errors.append(str(e))
            restored = self._snapshots.restore(task.id)
            if restored:
                self._state = restored
                logger.info(f"[{self.name}] ↩️ 已回滚 | task={task.id}")
            self._on_rollback(task, e)

        finally:
            result.finished_at = time.time()

        # 6. 附加性能指标
        result.metrics["elapsed"] = result.elapsed
        result.metrics["agent"] = self.name

        return result


# ── v1.0 → v2.0 适配器 ───────────────────────────

class AgentRunnerAdapter(AgentRunner):
    """
    将 v1.0 的 core.agent.Agent 包装为 v2.0 的 AgentRunner

    用法:
        from eduagent.core.agent import Agent  # v1.0
        from eduagent.framework.agent_runner import AgentRunnerAdapter

        class MyAgent(Agent): ...

        runner = AgentRunnerAdapter.wrap(MyAgent())
    """

    def __init__(self, name: str, agent_type: str, run_fn: Callable, timeout: int = 300):
        super().__init__(name=name, agent_type=agent_type, timeout=timeout)
        self._run_fn = run_fn

    async def _execute(self, task: Task) -> dict:
        """适配：Task → v1.0 Agent.run()"""
        # 调用 v1.0 Agent 的 run 方法（同步包装为异步）
        result = await asyncio.to_thread(
            self._run_fn,
            task.payload.get("task", task.payload.get("prompt", "")),
            **task.context,
        )
        # 如果 v1.0 返回的是 AgentMessage，提取 artifact
        if hasattr(result, 'artifact'):
            return {"output": result.artifact, "raw": result}
        if isinstance(result, dict):
            return result
        return {"output": str(result)}

    @classmethod
    def wrap(cls, v1_agent, agent_type: str = None, timeout: int = 300) -> "AgentRunnerAdapter":
        """
        一键包装 v1.0 Agent

        Args:
            v1_agent: eduagent.core.agent.Agent 实例
            agent_type: 类型标识（默认用 agent.name）
            timeout: 超时秒数
        """
        return cls(
            name=v1_agent.name,
            agent_type=agent_type or v1_agent.name,
            run_fn=v1_agent.run,
            timeout=timeout,
        )


# ── 隔离执行池 ───────────────────────────────────

class IsolatedExecutor:
    """
    隔离执行池 — 管理多个 AgentRunner 的并发执行

    每个 AgentRunner 有独立的：
      - 状态空间（不共享 _state）
      - 快照管理器（独立的回滚链）
      - 超时控制（per-task）
    """

    def __init__(self):
        self._agents: dict[str, AgentRunner] = {}

    def register(self, agent: AgentRunner):
        """注册 Agent 到池中"""
        self._agents[agent.agent_type] = agent

    def unregister(self, agent_type: str):
        self._agents.pop(agent_type, None)

    def get(self, agent_type: str) -> Optional[AgentRunner]:
        return self._agents.get(agent_type)

    async def execute_one(self, task: Task) -> Result:
        """执行单个任务"""
        agent = self._agents.get(task.type)
        if not agent:
            return Result.failure(task.id, [f"未找到类型为 '{task.type}' 的 Agent"])
        return await agent.execute(task)

    async def execute_parallel(self, tasks: list[Task]) -> dict[str, Result]:
        """
        🔥 并行执行 — 无依赖任务全部同时跑

        这是框架最核心的并行化能力：
        - 所有 tasks 用 asyncio.gather 同时启动
        - 每个 task 在隔离的 AgentRunner 上下文中执行
        - 单个失败不影响其他 task
        """
        if not tasks:
            return {}

        logger.info(f"🚀 并行派发 {len(tasks)} 个任务")
        start = time.time()

        results = await asyncio.gather(
            *[self.execute_one(t) for t in tasks],
            return_exceptions=True,
        )

        output: dict[str, Result] = {}
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                output[task.id] = Result.failure(task.id, [str(result)])
            else:
                output[task.id] = result

        elapsed = time.time() - start
        success_count = sum(1 for r in output.values() if r.ok)
        logger.info(
            f"🏁 并行执行完成 | {success_count}/{len(tasks)} 成功 | 耗时 {elapsed:.1f}s"
        )
        return output
