"""
EduAgent 记忆系统 —— 对话记忆 + 知识记忆双通道（支持持久化）
"""

import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """单条消息"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class Memory:
    """
    双通道记忆系统
    - conversation: 短期对话上下文（滑动窗口）
    - knowledge: 长期知识库（结构化存储）
    """

    def __init__(self, max_conversation_turns: int = 20):
        self._conversation: List[Message] = []
        self._knowledge: Dict[str, Any] = {}
        self.max_turns = max_conversation_turns

    # ─── 对话记忆 ─────────────────────────────

    def add_message(self, role: str, content: str, **meta):
        """添加一条对话消息"""
        self._conversation.append(Message(role=role, content=content, metadata=meta))
        self._trim()

    def get_context(self, last_n: int = 10) -> List[Dict[str, str]]:
        """获取最近 N 轮对话（LLM 格式）"""
        msgs = self._conversation[-last_n * 2:]  # 每轮 user+assistant
        return [{"role": m.role, "content": m.content} for m in msgs]

    def get_history(self) -> List[Message]:
        """获取全部对话历史"""
        return list(self._conversation)

    def clear_conversation(self):
        """清空对话记忆"""
        self._conversation.clear()

    def _trim(self):
        """保留最近 max_turns 轮对话"""
        if len(self._conversation) > self.max_turns * 2:
            self._conversation = self._conversation[-(self.max_turns * 2):]

    # ─── 知识记忆 ─────────────────────────────

    def set_knowledge(self, key: str, value: Any):
        """存储一条知识"""
        self._knowledge[key] = value

    def get_knowledge(self, key: str, default=None) -> Any:
        """获取一条知识"""
        return self._knowledge.get(key, default)

    def search_knowledge(self, query: str) -> List[str]:
        """简易关键词检索知识库"""
        results = []
        query_lower = query.lower()
        for key, value in self._knowledge.items():
            if query_lower in key.lower() or query_lower in str(value).lower():
                results.append(f"[{key}] {value}")
        return results

    def get_all_knowledge(self) -> Dict[str, Any]:
        return dict(self._knowledge)

    # ─── 持久化 ──────────────────────────────

    def save(self, filepath: str):
        """将记忆持久化到 JSON 文件"""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        data = {
            "conversation": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata,
                }
                for m in self._conversation
            ],
            "knowledge": self._knowledge,
            "max_turns": self.max_turns,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Memory":
        """从 JSON 文件恢复记忆"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        mem = cls(max_conversation_turns=data.get("max_turns", 20))
        for msg_data in data.get("conversation", []):
            mem._conversation.append(Message(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=msg_data.get("timestamp", ""),
                metadata=msg_data.get("metadata", {}),
            ))
        mem._knowledge = data.get("knowledge", {})
        return mem

    # ─── 序列化 ──────────────────────────────

    def summary(self) -> Dict[str, Any]:
        return {
            "conversation_turns": len(self._conversation) // 2,
            "knowledge_items": len(self._knowledge),
        }
