"""
EduAgent Agent 基类 —— 规划 → 执行 → 反思 三阶段循环
"""

import base64
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Literal

from openai import OpenAI

from .memory import Memory
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

# 输出模式
ModeType = Literal["brief", "standard", "detailed"]
ReflectType = Literal["auto", "always", "never"]

MODE_INSTRUCTIONS = {
    "brief": "请用精简格式输出，控制在一屏以内（约30行），只保留核心要点，省略详细展开和示例。",
    "standard": "请用标准格式输出，结构完整但不过度展开（约60行），重点突出，示例适量。",
    "detailed": "请详尽展开输出，包含完整推导、多个示例和深入分析（约100行以上），适合深度学习场景。",
}


class Agent(ABC):
    """
    教学 Agent 基类
    实现 规划(Plan) → 执行(Execute) → 反思(Reflect) 循环

    参数:
        mode: 输出模式 brief / standard / detailed
        reflection: 反思策略 auto(启发式自动) / always(始终反思) / never(跳过)
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
        max_iterations: int = 3,
        mode: ModeType = "standard",
        reflection: ReflectType = "auto",
        vision_model: Optional[str] = None,
    ):
        self.name = name
        self.memory = memory or Memory()
        self.tools = tools or ToolRegistry()
        self.model = model
        self.max_iterations = max_iterations
        self.mode: ModeType = mode
        self.reflection: ReflectType = reflection
        self.vision_model = vision_model or model  # 视觉模型，默认同文本模型
        self.client: Optional[OpenAI] = None

    def configure_llm(self, client: OpenAI):
        """注入 LLM 客户端（由 Orchestrator 统一管理）"""
        self.client = client

    def load_template(self, name: str) -> str:
        """加载 outputs/ 目录中的输出模板"""
        template_dir = Path(__file__).resolve().parent.parent / "outputs"
        tmpl_path = template_dir / f"{name}.md"
        if not tmpl_path.exists():
            raise FileNotFoundError(f"模板不存在: {tmpl_path}")
        return tmpl_path.read_text(encoding="utf-8")

    # ─── 主流程 ────────────────────────────────

    def run(self, task: str, **context) -> str:
        """
        执行任务的主入口
        1. Plan — 理解任务，制定计划
        2. Execute — 调用工具或直接生成
        3. Reflect — 检查结果，必要时迭代
        """
        # 将 mode 注入上下文，供子类 prompt 使用
        context["mode"] = self.mode
        context["mode_instruction"] = MODE_INSTRUCTIONS[self.mode]

        plan = self._plan(task, context)
        logger.info(f"[{self.name}] 计划: {plan[:200]}...")

        result = self._execute(plan, task, context)

        # 反思阶段：根据策略决定是否执行
        should_reflect = self._should_reflect(result)
        if should_reflect:
            for i in range(self.max_iterations):
                if self._reflect(result, task):
                    logger.info(f"[{self.name}] 反思通过 ✓")
                    break
                logger.info(f"[{self.name}] 反思未通过，重新执行 ({i+1}/{self.max_iterations})")
                result = self._execute(plan, task, context)
        else:
            logger.info(f"[{self.name}] 跳过反思 (策略: {self.reflection})")

        result = self._clean_output(result)
        self.memory.add_message("assistant", result)
        return result

    # ─── 输出清理 ──────────────────────────────

    def _clean_output(self, text: str) -> str:
        """去除 markdown 代码块包装，保留纯内容"""
        # 去掉 ```markdown 和结尾的 ```
        text = text.strip()
        text = re.sub(r'^```(?:markdown|md)?\s*\n?', '', text, count=1)
        text = re.sub(r'\n?```\s*$', '', text, count=1)
        return text.strip()

    # ─── 反思策略 ──────────────────────────────

    def _should_reflect(self, result: str) -> bool:
        """判断是否需要执行反思"""
        if self.reflection == "always":
            return True
        if self.reflection == "never":
            return False
        # auto: 启发式判断 — 结构良好的输出跳过反思
        if self.mode == "brief":
            return False  # 简版不反思
        # 检查是否有 markdown 结构标记
        if not re.search(r'^#+\s', result, re.MULTILINE):
            return True  # 没有标题结构，需要反思
        if len(result) < 200:
            return True  # 太短，可能不完整
        # 有完整结构 + 足够长度 → 跳过反思
        return False

    # ─── 三阶段实现 ────────────────────────────

    def _plan(self, task: str, context: Dict[str, Any]) -> str:
        """阶段1: 规划 — 分析任务，拆解为步骤"""
        mode_hint = context.get("mode_instruction", "")
        prompt = f"""你是一个任务规划器。请将以下任务拆解为清晰的执行步骤。

任务: {task}
输出模式: {mode_hint}
上下文: {json.dumps(context, ensure_ascii=False) if context else "无"}

请用简洁的编号列表输出执行计划（不超过5步）。"""
        response = self._call_llm(prompt, role="plan")
        return response

    def _execute(self, plan: str, task: str, context: Dict[str, Any]) -> str:
        """阶段2: 执行 — 根据计划调用工具或生成内容"""
        system = self.get_system_prompt()
        mode_hint = context.get("mode_instruction", "")

        user_prompt = f"""任务: {task}
执行计划: {plan}
输出要求: {mode_hint}
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
            # 只存储标准 OpenAI 角色名，避免 "plan"/"reflect" 等自定义角色污染上下文
            store_role = role if role in ("user", "assistant", "system") else "assistant"
            self.memory.add_message(store_role, content)
            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def _call_llm_with_tools(self, system: str, prompt: str) -> str:
        """调用 LLM + 工具（Function Calling），支持多轮工具链式调用"""
        if not self.client:
            raise RuntimeError("LLM 客户端未配置")

        messages = [
            {"role": "system", "content": system},
            *self.memory.get_context(last_n=3),
            {"role": "user", "content": prompt},
        ]
        tool_schemas = self.tools.get_schema()
        max_tool_rounds = 5  # 防止无限循环

        try:
            for round_num in range(max_tool_rounds):
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    temperature=0.7,
                    max_tokens=4096,
                )

                msg = resp.choices[0].message

                # 无工具调用 → 返回文本结果
                if not msg.tool_calls:
                    content = msg.content or ""
                    self.memory.add_message("assistant", content)
                    return content

                # 有工具调用 → 逐个执行
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    func_args = json.loads(tc.function.arguments)
                    logger.info(
                        f"[{self.name}] 工具调用 (第{round_num+1}轮): "
                        f"{func_name}({func_args})"
                    )
                    try:
                        result = self.tools.call(func_name, **func_args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })
                    except Exception as e:
                        logger.error(f"工具 {func_name} 执行失败: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"工具错误: {e}",
                        })

                # 追加 assistant 消息（含 tool_calls）到上下文
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

            # 达到最大轮数仍未结束
            logger.warning(
                f"[{self.name}] 工具调用达到最大轮数 {max_tool_rounds}，返回最后一轮结果"
            )
            # 最后请求一次总结
            final_resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages + [{
                    "role": "user",
                    "content": "请基于以上工具调用结果，给出最终回答。",
                }],
                temperature=0.7,
                max_tokens=4096,
            )
            content = final_resp.choices[0].message.content or ""
            self.memory.add_message("assistant", content)
            return content

        except Exception as e:
            logger.error(f"LLM (tools) 调用失败: {e}")
            raise

    # ─── 视觉 LLM 调用 ─────────────────────────

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """将图片文件编码为 base64 data URI，用于多模态 LLM 调用"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        ext = path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime = mime_map.get(ext, "image/jpeg")

        data = path.read_bytes()
        # 图片过大时自动压缩（Qwen-VL 建议 < 20MB）
        if len(data) > 10 * 1024 * 1024:
            logger.warning(f"图片 {image_path} 超过 10MB，可能导致调用失败")
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    def _call_llm_vision(
        self,
        prompt: str,
        system: str = "",
        images: Optional[List[str]] = None,
        image_urls: Optional[List[str]] = None,
        role: str = "user",
    ) -> str:
        """
        调用视觉 LLM（支持图片输入）
        使用 OpenAI 兼容的多模态 content 格式：
        [{"type": "image_url", ...}, {"type": "text", ...}]
        """
        if not self.client:
            raise RuntimeError("LLM 客户端未配置，请先调用 configure_llm()")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend(self.memory.get_context(last_n=3))

        # 构建多模态 content 数组
        content_parts: List[Dict[str, Any]] = []

        # 添加本地图片（base64 编码）
        for img_path in (images or []):
            data_uri = self._encode_image(img_path)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
            })

        # 添加远程图片 URL
        for url in (image_urls or []):
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": url},
            })

        # 添加文本 prompt
        content_parts.append({"type": "text", "text": prompt})

        messages.append({"role": "user", "content": content_parts})

        try:
            resp = self.client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                temperature=0.3,  # 视觉任务用低温度，提高准确性
                max_tokens=4096,
            )
            content = resp.choices[0].message.content or ""
            store_role = role if role in ("user", "assistant", "system") else "assistant"
            self.memory.add_message(store_role, content)
            return content
        except Exception as e:
            logger.error(f"视觉 LLM 调用失败: {e}")
            raise
