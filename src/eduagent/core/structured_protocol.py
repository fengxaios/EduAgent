"""
结构化通信协议 —— 受 PentAGI 启发

Agent 间传递结构化 JSON 而非自然语言，
每个消息包含：任务、状态、产物、置信度。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class AgentStatus(str, Enum):
    """Agent 执行状态 — 受 PentAGI 三态回报启发"""
    SUCCESS = "success"       # 任务完成
    FAILED = "failed"         # 执行失败
    NEEDS_HUMAN = "needs_human"  # 需人工介入


@dataclass
class AgentMessage:
    """
    Agent 间通信的标准消息格式

    参考 PentAGI 的设计原则：
    1. 结构化 — 不传大段自然语言
    2. 状态显式 — 不允许静默
    3. 可验证 — 产物格式可客观检查
    """
    agent_name: str
    task: str
    status: AgentStatus = AgentStatus.SUCCESS
    artifact: str = ""           # 产物（核心输出）
    summary: str = ""            # 100字以内的摘要
    confidence: float = 1.0      # 置信度 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(**data)


@dataclass
class PipelineReport:
    """
    Pipeline 执行报告 — 受 PentAGI 自动报告生成启发

    从多个 Agent 输出自动汇总为结构化报告。
    """
    pipeline_name: str
    messages: List[AgentMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def success_rate(self) -> float:
        if not self.messages:
            return 0.0
        successes = sum(1 for m in self.messages if m.status == AgentStatus.SUCCESS)
        return successes / len(self.messages)

    @property
    def total_confidence(self) -> float:
        if not self.messages:
            return 0.0
        return sum(m.confidence for m in self.messages) / len(self.messages)

    def to_markdown(self) -> str:
        """生成人类可读的 Markdown 报告"""
        lines = [
            f"# Pipeline 执行报告: {self.pipeline_name}",
            f"",
            f"**生成时间**: {self.created_at}",
            f"**成功率**: {self.success_rate:.0%} ({sum(1 for m in self.messages if m.status == AgentStatus.SUCCESS)}/{len(self.messages)})",
            f"**平均置信度**: {self.total_confidence:.2f}",
            f"",
            "---",
            f"",
        ]

        for i, msg in enumerate(self.messages, 1):
            status_icon = {"success": "✅", "failed": "❌", "needs_human": "⚠️"}.get(msg.status, "❓")
            lines.extend([
                f"## {status_icon} Step {i}: {msg.agent_name}",
                f"",
                f"| 字段 | 值 |",
                f"|------|-----|",
                f"| 任务 | {msg.task[:80]}{'...' if len(msg.task) > 80 else ''} |",
                f"| 状态 | {msg.status} |",
                f"| 置信度 | {msg.confidence:.0%} |",
                f"| 摘要 | {msg.summary or 'N/A'} |",
                f"",
                f"### 产物",
                f"",
                msg.artifact,
                f"",
                "---",
                f"",
            ])

        # 交叉分析
        lines.extend([
            "## 交叉分析",
            "",
            "| Agent | 状态 | 置信度 | 产物长度 |",
            "|-------|------|--------|----------|",
        ])
        for m in self.messages:
            lines.append(f"| {m.agent_name} | {m.status} | {m.confidence:.0%} | {len(m.artifact)} 字 |")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "created_at": self.created_at,
            "success_rate": self.success_rate,
            "total_confidence": self.total_confidence,
            "message_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
        }
