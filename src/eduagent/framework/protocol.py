"""
📡 通信层 — 标准化 Task/Result 信封 (v2.0)

与 core.structured_protocol 的 AgentMessage 互补：
- AgentMessage: Agent 间自然语言通信（适合 v1.0 串行 pipeline）
- Task/Result:  结构化任务派发（适合 v2.0 DAG 并行调度）

设计原则：
  1. Task 自包含 — 下游 Agent 拿到就能干活，不需要回头问
  2. 验收清单前置 — criteria 写进 Task，跑完自动校验
  3. 失败可逆 — rollback_hint 告诉执行器失败了怎么善后
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid
import time


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AcceptanceCriteria:
    """验收清单 — 下游 Agent 执行完后自动校验"""
    checks: list[str] = field(default_factory=list)
    # 示例: ["输出至少10页", "每页不超过50字", "格式为.pptx"]

    def validate(self, result_data: dict) -> tuple[bool, list[str]]:
        """执行校验，返回 (是否通过, 失败项列表)"""
        return True, []


@dataclass
class Task:
    """
    标准化任务信封

    ┌──────────────┬──────────────────────────────────┐
    │ 字段          │ 说明                              │
    ├──────────────┼──────────────────────────────────┤
    │ id           │ 全局唯一任务ID                     │
    │ type         │ Agent类型路由 (e.g. "ppt", "code") │
    │ payload      │ 任务具体内容                       │
    │ context      │ 上游Agent的输出，按需传递           │
    │ criteria     │ 验收清单                           │
    │ rollback_hint│ 失败恢复提示                       │
    │ timeout      │ 超时秒数                           │
    │ priority     │ 优先级 0(最高)-9(最低)              │
    │ depends_on   │ 依赖的任务ID列表                   │
    └──────────────┴──────────────────────────────────┘
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""
    payload: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    criteria: AcceptanceCriteria = field(default_factory=AcceptanceCriteria)
    rollback_hint: str = "无特殊回滚需求"
    timeout: int = 300
    priority: int = 5
    depends_on: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "context": self.context,
            "criteria": self.criteria.checks,
            "rollback_hint": self.rollback_hint,
            "timeout": self.timeout,
            "priority": self.priority,
            "depends_on": self.depends_on,
        }


@dataclass
class Result:
    """
    标准化结果信封

    ┌──────────────┬──────────────────────────────────┐
    │ 字段          │ 说明                              │
    ├──────────────┼──────────────────────────────────┤
    │ task_id      │ 对应任务ID                        │
    │ status       │ 执行状态                           │
    │ data         │ 产出数据                           │
    │ errors       │ 错误信息列表                       │
    │ metrics      │ 性能指标 {耗时, 重试次数, ...}      │
    │ artifacts    │ 产物路径列表                       │
    │ next_hints   │ 给下游Agent的提示                  │
    └──────────────┴──────────────────────────────────┘
    """
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    next_hints: list[str] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def elapsed(self) -> float:
        return self.finished_at - self.started_at

    @property
    def ok(self) -> bool:
        return self.status == TaskStatus.SUCCESS

    @classmethod
    def success(cls, task_id: str, data: dict, **kwargs) -> "Result":
        return cls(task_id=task_id, status=TaskStatus.SUCCESS, data=data, **kwargs)

    @classmethod
    def failure(cls, task_id: str, errors: list[str], **kwargs) -> "Result":
        return cls(task_id=task_id, status=TaskStatus.FAILED, errors=errors, **kwargs)
