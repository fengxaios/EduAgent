"""
EduAgent Agent 基类 —— 规划 → 执行 → 反思 三阶段循环
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

from openai import OpenAI

from .memory import Memory
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class Agent(ABC):
    """
    教学 Agent 基类
    实现 规划(Plan) → 执行(Execute) → 反思(Reflect) 循环
    """

    # ─── 子类可覆写 ────────────────────────────

    @abstractmethod
    def get_system_prompt(self) -> str:
        """返回系统提示词，定义 Agent 的角色和能力"""
        ...

    # ─── 构造 ──────────────────────────────────

    def __init__(
        self,
        name: str,
        memory: Optional[Memory] = None,
        tools: Optional[ToolRegistry] = None,
        model: str = "qwen-plus",
        max_iterations: int = 5,
    ):
        self.name = name
        self.memory = memory or Memory()
        self.tools = tools or ToolRegistry()
        self.model = model
        self.max_iterations = max_iterations
        self.client: Optional[OpenAI] = None

    def configure_llm(self, client: OpenAI):
        """注入 LLM 客户端（由 Orchestrator 统一管理）"""
        self.client = client

    # ─── 主流程 ────────────────────────────────

    def run(self, task: str, **context) -> str:
        """
        执行任务的主入口
        1. Plan — 理解任务，制定计划
        2. Execute — 调用工具或直接生成
        3. Reflect — 检查结果，必要时迭代
        """
        plan = self._plan(task, context)
        logger.info(f"[{self.name}] 计划: {plan[:200]}...")

        result = self._execute(plan, task, context)

        for i in range(self.max_iterations):
            if self._reflect(result, task):
                logger.info(f"[{self.name}] 反思通过 ✓")
                break
            logger.info(f"[{self.name}] 反思未通过，重新执行 ({i+1}/{self.max_iterations})")
            result = self._execute(plan, task, context)

        self.memory.add_message("assistant", result)
        return result

    # ─── 三阶段实现 ────────────────────────────

    def _plan(self, task: str, context: Dict[str, Any]) -> str:
        """阶段1: 规划 — 分析任务，拆解为步骤"""
        prompt = f"""你是一个任务规划器。请将以下任务拆解为清晰的执行步骤。

任务: {task}
上下文: {json.dumps(context, ensure_ascii=False) if context else "无"}

请用简洁的编号列表输出执行计划（不超过5步）。"""
        response = self._call_llm(prompt, role="plan")
        return response

    def _execute(self, plan: str, task: str, context: Dict[str, Any]) -> str:
        """阶段2: 执行 — 根据计划调用工具或生成内容"""
        system = self.get_system_prompt()
        user_prompt = f"""任务: {task}
执行计划: {plan}
上下文: {json.dumps(context, ensure_ascii=False) if context else "无"}

请按照计划执行任务，输出最终结果。如需使用工具，请明确指出。"""

        if self.tools._tools:
            return self._call_llm_with_tools(system, user_prompt)
        else:
            return self._call_llm(user_prompt, system=system)

    def _reflect(self, result: str, task: str) -> bool:
        """阶段3: 反思 — 检查结果质量"""
        prompt = f"""请评估以下任务执行结果的质量。

原始任务: {task}
执行结果 (前500字): {result[:500]}

请回答:
1. 结果是否完成了任务要求？
2. 内容是否准确、完整？
3. 格式是否符合预期？

如果三项都通过，回复 "PASS"。否则回复 "FAIL: 原因"。"""
        response = self._call_llm(prompt, role="reflect")
        return response.strip().upper().startswith("PASS")

    # ─── LLM 调用 ─────────────────────────────

    def _call_llm(
        self,
        prompt: str,
        system: str = "",
        role: str = "user",
    ) -> str:
        """调用 LLM 生成文本"""
        if not self.client:
            raise RuntimeError("LLM 客户端未配置，请先调用 configure_llm()")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        # 注入最近对话上下文
        messages.extend(self.memory.get_context(last_n=3))
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            content = resp.choices[0].message.content or ""
            self.memory.add_message(role, content)
            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def _call_llm_with_tools(self, system: str, prompt: str) -> str:
        """调用 LLM + 工具（Function Calling）"""
        if not self.client:
            raise RuntimeError("LLM 客户端未配置")

        messages = [
            {"role": "system", "content": system},
            *self.memory.get_context(last_n=3),
            {"role": "user", "content": prompt},
        ]
        tool_schemas = self.tools.get_schema()

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=0.7,
                max_tokens=4096,
            )

            msg = resp.choices[0].message

            # 处理工具调用
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    func_args = json.loads(tc.function.arguments)
                    logger.info(f"[{self.name}] 调用工具: {func_name}({func_args})")
                    try:
                        result = self.tools.call(func_name, **func_args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"工具错误: {e}",
                        })

                # 继续对话获取最终结果
                final_resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096,
                )
                content = final_resp.choices[0].message.content or ""
            else:
                content = msg.content or ""

            self.memory.add_message("assistant", content)
            return content

        except Exception as e:
            logger.error(f"LLM (tools) 调用失败: {e}")
            raise
