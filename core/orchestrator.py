"""
EduAgent 多 Agent 编排器 —— 负责任务分发与 Agent 协作
"""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .agent import Agent

# 自动加载 .env 配置
load_dotenv()

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    多 Agent 编排器
    - 管理多个教学 Agent
    - 按任务类型路由到对应 Agent
    - 支持 Agent 间的串行协作
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen-plus",
    ):
        self.agents: Dict[str, Agent] = {}
        self.model = model

        # 初始化 LLM 客户端
        api_key = api_key or self._env("DASHSCOPE_API_KEY")
        base_url = base_url or self._env(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        if not api_key or api_key.startswith("your_api_key"):
            raise ValueError(
                "请设置环境变量 DASHSCOPE_API_KEY，"
                "或通过 Orchestrator(api_key='...') 传入"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def register(self, agent: Agent):
        """注册一个 Agent"""
        agent.configure_llm(self.client)
        agent.model = self.model  # 统一使用编排器的模型配置
        self.agents[agent.name] = agent
        logger.info(f"Agent 注册: {agent.name}")

    def register_all(self, agents: List[Agent]):
        """批量注册 Agent"""
        for agent in agents:
            self.register(agent)

    def route(self, task: str, **context) -> Dict[str, Any]:
        """
        智能路由：根据任务描述自动选择最合适的 Agent
        """
        if not self.agents:
            raise RuntimeError("没有注册任何 Agent，请先调用 register()")

        # 用 LLM 分析任务，选择 Agent
        agent_names = list(self.agents.keys())
        agent_descs = "\n".join(
            f"- {name}: {agent.get_system_prompt()[:100]}..."
            for name, agent in self.agents.items()
        )

        prompt = f"""以下是一个教学任务，请从可用 Agent 中选择最合适的一个。

任务: {task}

可用 Agent:
{agent_descs}

请只回复 Agent 的名称（从 {agent_names} 中选择一个），不要输出其他内容。"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=50,
            )
            chosen = resp.choices[0].message.content.strip()
            for name in agent_names:
                if name in chosen:
                    logger.info(f"路由: '{task[:50]}...' → {name}")
                    result = self.agents[name].run(task, **context)
                    return {"agent": name, "result": result}
        except Exception as e:
            logger.warning(f"自动路由失败，使用第一个 Agent: {e}")

        # fallback: 使用第一个 Agent
        first = list(self.agents.keys())[0]
        result = self.agents[first].run(task, **context)
        return {"agent": first, "result": result}

    def pipeline(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        管线执行：多个 Agent 串行协作
        tasks 格式: [{"agent": "lesson_planner", "task": "..."}, ...]
        """
        results = []
        shared_context = {}

        for item in tasks:
            agent_name = item.get("agent")
            task = item.get("task", "")

            if agent_name and agent_name in self.agents:
                result = self.agents[agent_name].run(task, **shared_context)
                shared_context["previous_result"] = result
                results.append({"agent": agent_name, "task": task, "result": result})
            else:
                results.append({
                    "agent": agent_name,
                    "task": task,
                    "error": f"Agent '{agent_name}' 未注册",
                })

        return results

    def get_status(self) -> Dict[str, Any]:
        """获取编排器状态"""
        return {
            "model": self.model,
            "registered_agents": list(self.agents.keys()),
            "agent_count": len(self.agents),
        }

    @staticmethod
    def _env(key: str, default: str = "") -> str:
        return os.getenv(key, default)
