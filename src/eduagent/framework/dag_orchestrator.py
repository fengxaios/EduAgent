"""
🧠 DAGOrchestrator — DAG并行调度中枢 (v2.0)

与 core.orchestrator.Orchestrator 互补：
- Orchestrator:       LLM路由 + 串行pipeline（v1.0）
- DAGOrchestrator:    DAG分层并行 + 自动重试 + 上下文管理（v2.0）

可以独立使用，也可以包装已有的 Orchestrator 实例。
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .protocol import Task, Result, TaskStatus
from .agent_runner import AgentRunner, IsolatedExecutor, AgentRunnerAdapter
from .context import ContextManager

logger = logging.getLogger(__name__)


# ── DAG 节点 ──────────────────────────────────────

@dataclass
class DAGNode:
    task: Task
    children: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    level: int = 0  # 拓扑层级（0=根节点）


# ── DAGOrchestrator ──────────────────────────────

class DAGOrchestrator:
    """
    DAG 并行调度器 (v2.0)

    核心升级（相比 v1.0 Orchestrator）：
      1. DAG 依赖解析 → 按拓扑层级分层
      2. 同层任务并行执行（asyncio.gather）
      3. 下游自动获取上游 context
      4. 失败自动重试 + 快照回滚
      5. 上下文 WAL 管理

    用法:
        orch = DAGOrchestrator()
        orch.register(ppt_runner)
        orch.register(knowledge_runner)

        tasks = [
            Task(id="ppt", type="ppt", depends_on=[]),
            Task(id="exer", type="exercise", depends_on=["knowledge"]),
        ]
        results = await orch.run_dag(tasks)
    """

    def __init__(self, max_parallel: int = 10):
        self.executor = IsolatedExecutor()
        self.context = ContextManager()
        self.max_parallel = max_parallel
        self._task_decomposer: Optional[Callable] = None

    # ── Agent 注册 ─────────────────────────────────

    def register(self, agent: AgentRunner):
        """注册 AgentRunner"""
        self.executor.register(agent)

    def register_v1(self, v1_agent, agent_type: str = None):
        """
        一键注册 v1.0 Agent

        Args:
            v1_agent: eduagent.core.agent.Agent 实例
            agent_type: 类型标识（默认用 agent.name）
        """
        adapter = AgentRunnerAdapter.wrap(v1_agent, agent_type=agent_type)
        self.executor.register(adapter)
        return adapter

    def set_decomposer(self, fn: Callable):
        """注入任务拆解函数（通常是 LLM 调用）"""
        self._task_decomposer = fn

    # ── DAG 构建 ───────────────────────────────────

    def build_dag(self, tasks: list[Task]) -> dict[str, DAGNode]:
        """
        从 Task 的 depends_on 字段构建 DAG

        自动计算每个节点的拓扑层级：
          level 0 = 无依赖，可立即并行
          level 1 = 依赖 level 0 完成
          level 2 = 依赖 level 1 完成
          ...

        Raises:
            ValueError: 检测到循环依赖时抛出
        """
        nodes: dict[str, DAGNode] = {}

        for t in tasks:
            nodes[t.id] = DAGNode(task=t)

        for t in tasks:
            node = nodes[t.id]
            for dep_id in t.depends_on:
                if dep_id in nodes:
                    node.parents.append(dep_id)
                    nodes[dep_id].children.append(t.id)

        # ── 环检测 (DFS三色标记法) ──
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in nodes}

        def _has_cycle(nid: str) -> bool:
            color[nid] = GRAY
            for child_id in nodes[nid].children:
                if color[child_id] == GRAY:
                    return True  # 回边 → 有环
                if color[child_id] == WHITE:
                    if _has_cycle(child_id):
                        return True
            color[nid] = BLACK
            return False

        for nid in nodes:
            if color[nid] == WHITE:
                if _has_cycle(nid):
                    raise ValueError(
                        f"检测到循环依赖，涉及节点: {nid}。"
                        f"请检查 Task.depends_on 关系。"
                    )

        # 拓扑层级（BFS）
        level0 = [nid for nid, node in nodes.items() if not node.parents]
        visited = set()
        queue = [(nid, 0) for nid in level0]

        while queue:
            nid, level = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            nodes[nid].level = max(nodes[nid].level, level)
            for child_id in nodes[nid].children:
                if child_id not in visited:
                    queue.append((child_id, level + 1))

        return nodes

    # ── 分层并行执行 ───────────────────────────────

    async def run_dag(
        self,
        tasks: list[Task],
        on_level_complete: Optional[Callable] = None,
    ) -> dict[str, Result]:
        """
        按 DAG 层级串行，层内并行执行

        算法:
          while 还有未完成的层级:
            找出当前层级所有 ready 的节点
            → asyncio.gather 并行执行
            → 收集结果，注入下游 task.context
            → 进入下一层级
        """
        if not tasks:
            return {}

        nodes = self.build_dag(tasks)
        max_level = max(n.level for n in nodes.values())
        all_results: dict[str, Result] = {}

        by_level: dict[int, list[str]] = defaultdict(list)
        for nid, node in nodes.items():
            by_level[node.level].append(nid)

        logger.info(f"📊 DAG: {len(tasks)} tasks, {max_level + 1} 层级")

        for level in range(max_level + 1):
            level_ids = by_level[level]
            level_tasks = []

            for nid in level_ids:
                t = nodes[nid].task
                # 🔥 注入上游结果到下游 task.context
                if nodes[nid].parents:
                    for parent_id in nodes[nid].parents:
                        if parent_id in all_results and all_results[parent_id].ok:
                            parent_agent = nodes[parent_id].task.type
                            t.context[parent_agent] = all_results[parent_id].data
                level_tasks.append(t)

            # 🔥 层内并行执行
            logger.info(f"  ├─ Level {level}: {len(level_tasks)} tasks → 并行")
            results = await asyncio.gather(
                *[self.executor.execute_one(t) for t in level_tasks],
                return_exceptions=True,
            )

            for task, result in zip(level_tasks, results):
                if isinstance(result, Exception):
                    all_results[task.id] = Result.failure(task.id, [str(result)])
                else:
                    all_results[task.id] = result
                    if result.ok:
                        self.context.update_state(f"result:{task.id}", result.data)

            if on_level_complete:
                on_level_complete(level, {k: all_results[k] for k in level_ids})

        return all_results

    # ── 端到端：需求 → DAG → 并行执行 → 汇总 ──────

    async def run(
        self,
        requirement: str,
        decomposer: Optional[Callable] = None,
    ) -> dict[str, Result]:
        """
        端到端执行：需求 → 拆解 → DAG → 并行执行 → 汇总

        Args:
            requirement: 自然语言需求描述
            decomposer: 自定义拆解函数（默认用 self._task_decomposer）
        """
        fn = decomposer or self._task_decomposer
        if not fn:
            raise RuntimeError(
                "未设置任务拆解函数。请先 set_decomposer() 或传入 decomposer 参数。"
            )

        logger.info(f"🔍 拆解需求: {requirement}")
        tasks = await fn(requirement)
        if isinstance(tasks, Task):
            tasks = [tasks]

        nodes = self.build_dag(tasks)
        results = await self.run_dag(tasks)
        results = await self._quality_check_and_retry(results, nodes)
        return results

    # ── 质量校验 + 重试 ────────────────────────────

    async def _quality_check_and_retry(
        self,
        results: dict[str, Result],
        nodes: dict[str, Any],
        max_retries: int = 2,
    ) -> dict[str, Result]:
        """对失败任务按优先级重试"""
        failed = [
            (tid, r) for tid, r in results.items()
            if not r.ok and r.status != TaskStatus.CANCELLED
        ]
        if not failed:
            return results

        for attempt in range(max_retries):
            if not failed:
                break
            logger.info(f"🔄 重试第 {attempt + 1}/{max_retries} 轮: {len(failed)} tasks")
            retry_tasks = [nodes[tid].task for tid, _ in failed]
            new_results = await asyncio.gather(
                *[self.executor.execute_one(t) for t in retry_tasks],
                return_exceptions=True,
            )
            failed = []
            for task, result in zip(retry_tasks, new_results):
                if isinstance(result, Exception):
                    failed.append((task.id, Result.failure(task.id, [str(result)])))
                elif not result.ok:
                    failed.append((task.id, result))
                else:
                    results[task.id] = result

        return results

    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "version": "2.0",
            "agents": list(self.executor._agents.keys()),
            "context_version": self.context._state.version,
            "max_parallel": self.max_parallel,
        }
