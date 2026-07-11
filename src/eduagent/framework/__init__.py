"""
EduAgent v2.0 — 多Agent分布式指挥框架

与 core 层互补：
- core.orchestrator.Orchestrator:     LLM路由 + 串行pipeline (v1.0)
- framework.dag_orchestrator.DAGOrchestrator: DAG并行调度 (v2.0)

- core.agent.Agent:                   Plan→Execute→Reflect 三阶段 (v1.0)
- framework.agent_runner.AgentRunner:  Snapshot→Execute→Verify→Rollback (v2.0)

核心能力：
  1. 🧠 并行调度 — DAG分层并行执行，同层任务asyncio.gather同时跑
  2. 🛡️ 容错系统 — 指数退避重试 + 熔断器 + 快照回滚
  3. ⏰ 自动化   — Cron定时调度 + Workflow工作流引擎
  4. 📡 结构化通信 — Task/Result 信封 + 验收清单 + 上下文WAL

快速开始：
  from eduagent.framework import (
      DAGOrchestrator, Task, Result,
      AgentRunner, AgentRunnerAdapter,
      RetryPolicy, CircuitBreaker,
      CronScheduler, WorkflowEngine,
  )

  # 方式1: 使用新Agent（继承AgentRunner）
  class MyAgent(AgentRunner):
      async def _execute(self, task: Task) -> dict:
          return {"output": "done"}

  # 方式2: 包装现有 v1.0 Agent
  from eduagent.core.agent import Agent  # v1.0
  adapter = AgentRunnerAdapter.wrap(my_v1_agent)
"""

# 通信协议
from .protocol import Task, Result, TaskStatus, AcceptanceCriteria

# 调度核心
from .dag_orchestrator import DAGOrchestrator, DAGNode

# Agent 执行器
from .agent_runner import (
    AgentRunner,
    AgentRunnerAdapter,
    IsolatedExecutor,
    SnapshotManager,
)

# 上下文管理
from .context import ContextManager, SharedState

# 容错系统
from .fault_tolerance import (
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerOpenError,
)

# 自动化系统
from .automation import (
    CronScheduler,
    CronParser,
    WorkflowEngine,
    WorkflowStep,
)

__all__ = [
    # Protocol
    "Task", "Result", "TaskStatus", "AcceptanceCriteria",
    # Orchestrator
    "DAGOrchestrator", "DAGNode",
    # Agents
    "AgentRunner", "AgentRunnerAdapter", "IsolatedExecutor", "SnapshotManager",
    # Context
    "ContextManager", "SharedState",
    # Fault Tolerance
    "RetryPolicy", "CircuitBreaker", "CircuitBreakerOpenError",
    # Automation
    "CronScheduler", "CronParser", "WorkflowEngine", "WorkflowStep",
]
