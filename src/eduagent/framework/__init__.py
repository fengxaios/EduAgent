"""
EduAgent v2.1 — 多Agent分布式指挥框架 + 协作模式

与 core 层互补：
- core.orchestrator.Orchestrator:     LLM路由 + 串行pipeline (v1.0)
- framework.dag_orchestrator.DAGOrchestrator: DAG并行调度 (v2.0)
- framework.collaboration:            群聊/交接/共享记忆 (v2.1)

核心能力：
  1. 🧠 并行调度 — DAG分层并行执行，同层任务asyncio.gather同时跑
  2. 🛡️ 容错系统 — 指数退避重试 + 熔断器 + 快照回滚
  3. ⏰ 自动化   — Cron定时调度 + Workflow工作流引擎
  4. 📡 结构化通信 — Task/Result 信封 + 验收清单 + 上下文WAL
  5. 🤝 协作模式 — GroupChat群聊 + AgentHandoff交接 + SharedMemory共享记忆
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

# 协作模式 (v2.1)
from .collaboration import (
    GroupChat, GroupChatConfig, ChatMessage, MessageType,
    AgentHandoff, HandoffContext,
    SharedMemory, MemoryEntry,
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
    # Collaboration (v2.1)
    "GroupChat", "GroupChatConfig", "ChatMessage", "MessageType",
    "AgentHandoff", "HandoffContext",
    "SharedMemory", "MemoryEntry",
]
