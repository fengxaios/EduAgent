"""
🤝 多Agent协作模式 — GroupChat + Debate + Handoff (v2.1)

基于 2026 年 Multi-Agent 研究增强：
- Group Chat (AutoGen 3.0 / AG2): 群聊式多Agent协商
- Hierarchical (CrewAI): Manager → Worker 层次化
- Agent-to-Agent Handoff: 标准化上下文传递
- Shared Memory: 跨会话集体记忆
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 消息类型
# ═══════════════════════════════════════════════

class MessageType(Enum):
    CHAT = "chat"            # 普通对话
    PROPOSAL = "proposal"    # 提案（等待投票）
    VOTE = "vote"            # 投票
    RESULT = "result"        # 结果
    HANDOFF = "handoff"      # Agent交接
    SYSTEM = "system"        # 系统消息


@dataclass
class ChatMessage:
    """群聊消息"""
    sender: str
    content: str
    msg_type: MessageType = MessageType.CHAT
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


# ═══════════════════════════════════════════════
# GroupChat — 群聊协作模式 (AutoGen 启发)
# ═══════════════════════════════════════════════

@dataclass
class GroupChatConfig:
    """群聊配置"""
    max_rounds: int = 10               # 最大对话轮次
    min_agents_to_respond: int = 2     # 最少需要几个Agent响应
    consensus_threshold: float = 0.67  # 达成共识的阈值
    turn_timeout: float = 30.0         # 单轮超时(秒)


class GroupChat:
    """
    群聊协作室 — 多个Agent在同一空间讨论

    流程：
    1. 提问者发起话题
    2. 各Agent轮流发言
    3. 可发起投票/提案
    4. 达成共识或达到轮次上限后结束

    Example:
        chat = GroupChat()
        chat.add_agent("planner", planner_fn)
        chat.add_agent("critic", critic_fn)
        result = await chat.discuss("如何设计这节教案？")
    """

    def __init__(self, config: Optional[GroupChatConfig] = None):
        self.config = config or GroupChatConfig()
        self.agents: Dict[str, Callable] = {}
        self.history: List[ChatMessage] = []
        self.round = 0
        self._votes: Dict[str, Dict[str, str]] = {}  # topic → {agent: vote}

    def add_agent(self, name: str, agent_fn: Callable):
        """注册Agent到群聊 (agent_fn: prompt → response)"""
        self.agents[name] = agent_fn

    def add_message(self, msg: ChatMessage):
        self.history.append(msg)

    def get_recent_context(self, n: int = 5) -> str:
        """获取最近n条消息作为上下文"""
        recent = self.history[-n:]
        lines = []
        for msg in recent:
            tag = f"[{msg.msg_type.value}]" if msg.msg_type != MessageType.CHAT else ""
            lines.append(f"{tag}{msg.sender}: {msg.content[:200]}")
        return "\n".join(lines)

    async def discuss(self, topic: str, initiator: str = "user") -> Dict[str, Any]:
        """
        发起群聊讨论

        Returns:
            {"conclusion": str, "rounds": int, "participants": [str], "history": [...]}
        """
        self.round = 0
        self._votes = {}

        # 初始消息
        self.add_message(ChatMessage(
            sender=initiator, content=topic, msg_type=MessageType.SYSTEM
        ))

        conclusions = []

        while self.round < self.config.max_rounds:
            self.round += 1
            round_responses = []
            context = self.get_recent_context()

            # 每个Agent轮流传话
            for name, agent_fn in self.agents.items():
                try:
                    prompt = f"""[讨论轮次 {self.round}]
话题: {topic}

近期讨论:
{context}

你叫 {name}，请针对当前讨论给出你的看法。
如果同意前面某个Agent的观点，请直接说"同意"并补充理由。
如果不同意，请说明理由并提出你的方案。
每轮回复控制在100字以内。"""

                    response = await agent_fn(prompt)
                    msg = ChatMessage(sender=name, content=response[:300])
                    self.add_message(msg)
                    round_responses.append({"agent": name, "response": response[:300]})

                except Exception as e:
                    logger.warning(f"[GroupChat] {name} 响应失败: {e}")

            # 检查是否达成共识
            if self._check_consensus(topic):
                conclusion = self._build_conclusion()
                return {
                    "conclusion": conclusion,
                    "rounds": self.round,
                    "participants": list(self.agents.keys()),
                    "history": [
                        {"sender": m.sender, "content": m.content[:100], "type": m.msg_type.value}
                        for m in self.history
                    ],
                }

        # 达到最大轮次，返回当前状态
        return {
            "conclusion": self._build_conclusion() or "未达成共识",
            "rounds": self.round,
            "participants": list(self.agents.keys()),
            "history": [{"sender": m.sender, "content": m.content[:100]} for m in self.history],
        }

    def propose(self, topic: str, proposal: str, proposer: str):
        """发起提案，等待投票"""
        self.add_message(ChatMessage(
            sender=proposer, content=proposal, msg_type=MessageType.PROPOSAL,
            metadata={"topic": topic},
        ))
        self._votes[topic] = {}

    def vote(self, topic: str, agent: str, choice: str):
        """投票: agree / disagree / abstain"""
        if topic not in self._votes:
            self._votes[topic] = {}
        self._votes[topic][agent] = choice

    def _check_consensus(self, topic: str) -> bool:
        """检查是否达成共识"""
        if topic not in self._votes:
            return False
        votes = self._votes[topic]
        if not votes:
            return False
        agrees = sum(1 for v in votes.values() if v == "agree")
        return agrees / len(votes) >= self.config.consensus_threshold

    def _build_conclusion(self) -> str:
        """从历史中提取结论"""
        recent = self.history[-3:]
        for msg in reversed(recent):
            if msg.msg_type == MessageType.RESULT:
                return msg.content
        return ""


# ═══════════════════════════════════════════════
# AgentHandoff — Agent间交接 (Handoff模式)
# ═══════════════════════════════════════════════

@dataclass
class HandoffContext:
    """
    交接上下文 — Agent A 传递给 Agent B 的标准化信息

    - task: 当前任务描述
    - previous_output: 上游Agent产出
    - pending_decisions: 待决策事项
    - shared_memory_key: 共享记忆索引
    """
    task: str
    previous_output: str = ""
    pending_decisions: List[str] = field(default_factory=list)
    shared_memory_key: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentHandoff:
    """
    Agent 交接链 — 支持顺序/条件/广播三种模式

    顺序模式: A → B → C (串行)
    条件模式: A → (B if X else C) (分支)
    广播模式: A → B, C, D (并行扇出)
    """

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        """注册Agent处理器"""
        self.handlers[name] = handler

    async def sequential(
        self,
        chain: List[Tuple[str, str]],
        initial_context: Optional[HandoffContext] = None,
    ) -> List[Dict[str, Any]]:
        """
        顺序交接: A→B→C

        chain: [(agent_name, task_description), ...]
        """
        results = []
        context = initial_context or HandoffContext(task="")

        for agent_name, task in chain:
            if agent_name not in self.handlers:
                results.append({"agent": agent_name, "error": "未注册"})
                continue

            context.task = task
            try:
                output = await self.handlers[agent_name](context)
                context.previous_output = str(output)
                results.append({"agent": agent_name, "output": output})
            except Exception as e:
                results.append({"agent": agent_name, "error": str(e)})
                break

        return results

    async def broadcast(
        self,
        tasks: Dict[str, str],
        shared_context: Optional[HandoffContext] = None,
    ) -> Dict[str, Any]:
        """
        广播扇出: 一个任务分派给多个Agent并行执行
        tasks: {agent_name: task_description, ...}
        """
        context = shared_context or HandoffContext(task="")
        results = {}

        async def run_agent(name: str, task: str) -> Tuple[str, Any]:
            if name in self.handlers:
                ctx = HandoffContext(task=task, previous_output=context.previous_output)
                try:
                    return name, await self.handlers[name](ctx)
                except Exception as e:
                    return name, {"error": str(e)}
            return name, {"error": "未注册"}

        tasks_list = [run_agent(name, task) for name, task in tasks.items()]
        completed = await asyncio.gather(*tasks_list)
        for name, output in completed:
            results[name] = output

        return results


# ═══════════════════════════════════════════════
# SharedMemory — 跨Agent共享记忆 (EduClaw 启发)
# ═══════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """共享记忆条目"""
    key: str
    value: Any
    source_agent: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class SharedMemory:
    """
    跨Agent共享记忆 — 所有Agent可读可写

    支持:
    - 结构化存取 (key-value)
    - 标签检索 (按tag过滤)
    - 时间线回溯 (按时间范围)
    """

    def __init__(self):
        self._store: Dict[str, MemoryEntry] = {}

    def put(self, key: str, value: Any, source: str = "", tags: Optional[List[str]] = None):
        """写入共享记忆"""
        self._store[key] = MemoryEntry(
            key=key, value=value, source_agent=source, tags=tags or [],
        )

    def get(self, key: str, default: Any = None) -> Any:
        """读取共享记忆"""
        entry = self._store.get(key)
        return entry.value if entry else default

    def search(self, tag: str) -> List[MemoryEntry]:
        """按标签检索"""
        return [e for e in self._store.values() if tag in e.tags]

    def get_all_since(self, since: float) -> List[MemoryEntry]:
        """获取某个时间点之后的所有条目"""
        return [e for e in self._store.values() if e.timestamp >= since]

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: {
                "value": v.value if not isinstance(v.value, (str, int, float, bool, list, dict))
                       else v.value,
                "source": v.source_agent,
                "tags": v.tags,
                "timestamp": v.timestamp,
            }
            for k, v in self._store.items()
        }

    def clear(self):
        self._store.clear()
