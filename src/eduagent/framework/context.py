"""
📋 上下文管理器 — 状态传递与漂移防护 (v2.0)

与 core.memory 互补：
- Memory:  长期记忆存储（知识、偏好）
- ContextManager: 单次调度中的状态传递（WAL + 原子化快照）

核心问题：多个 Agent 并发时，如何保证状态一致？
答案：状态原子化共享 + 只传结构化数据，不传对话历史。

设计灵感：Moltcup 的上下文漂移治理原则
  - 每个 Agent 的上下文独立，不共享对话历史
  - 只传递结构化状态快照（SharedState）
  - 状态变更记录 WAL（Write-Ahead Log）便于回滚
"""

from dataclasses import dataclass, field
from typing import Any
import time
from collections import deque


@dataclass
class SharedState:
    """
    全局共享状态快照
    所有 Agent 都能读取，但只有 Orchestrator 能写入。
    每次写入生成一个新版本号，形成不可变历史链。
    """
    version: int = 0
    data: dict = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def to_dict(self) -> dict:
        return {"version": self.version, "data": self.data}


class ContextManager:
    """
    上下文管理器

    职责：
      1. 维护全局 SharedState（单写多读）
      2. 管理 WAL（Write-Ahead Log）用于回滚
      3. 为每个 Agent 裁剪最小必要上下文
      4. 防止上下文漂移 — 不传对话历史，只传结构化数据
    """

    def __init__(self, max_wal_entries: int = 100):
        self._state = SharedState()
        self._wal: deque[dict] = deque(maxlen=max_wal_entries)
        self._agent_contexts: dict[str, dict] = {}

    # ── 状态读写 ──────────────────────────────────

    def update_state(self, key: str, value: Any) -> int:
        """写入全局状态（仅 Orchestrator 调用），返回新版本号"""
        old_value = self._state.data.get(key)
        self._state.version += 1
        self._state.data[key] = value
        self._state.updated_at = time.time()

        # 写 WAL
        self._wal.append({
            "version": self._state.version,
            "op": "SET",
            "key": key,
            "old": old_value,
            "new": value,
            "ts": time.time(),
        })
        return self._state.version

    def get_snapshot(self) -> SharedState:
        """获取当前状态只读快照"""
        return SharedState(
            version=self._state.version,
            data=dict(self._state.data),
        )

    def rollback_to_version(self, target_version: int) -> bool:
        """回滚到指定版本"""
        if target_version >= self._state.version:
            return False
        while self._state.version > target_version and self._wal:
            entry = self._wal.pop()
            if entry["op"] == "SET":
                if entry["old"] is None:
                    self._state.data.pop(entry["key"], None)
                else:
                    self._state.data[entry["key"]] = entry["old"]
            self._state.version -= 1
        return True

    # ── Agent 上下文裁剪 ──────────────────────────

    def build_agent_context(
        self,
        agent_type: str,
        upstream_results: dict[str, Any] = None,
        required_state_keys: list[str] = None,
    ) -> dict:
        """
        为特定 Agent 构建最小必要上下文
        - 不传对话历史
        - 只传该 Agent 需要的那几项状态
        - 包含上游 Agent 的结构化输出
        """
        ctx = {
            "agent_type": agent_type,
            "timestamp": time.time(),
            "upstream": upstream_results or {},
        }
        if required_state_keys:
            ctx["state"] = {
                k: self._state.data[k]
                for k in required_state_keys
                if k in self._state.data
            }
        else:
            ctx["state"] = {}
        self._agent_contexts[agent_type] = ctx
        return ctx

    # ── WAL 查询 ──────────────────────────────────

    def get_recent_changes(self, limit: int = 10) -> list[dict]:
        """查看最近的状态变更"""
        return list(self._wal)[-limit:]
