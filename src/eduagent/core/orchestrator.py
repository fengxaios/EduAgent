"""
EduAgent 多 Agent 编排器 —— 负责任务分发与 Agent 协作（2026 增强版）

基于 2026 年前沿研究增强：
- Agent Scaling Law (EduClaw): Agent 能力 = Profile 结构丰富度的函数
- ZPD-aware routing (AgentSchool): 沿最近发展区自适应教学
- MAIC 三组件架构: 课程生成 + 自适应引擎 + 多智能体课堂
"""

import logging
import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from openai import OpenAI

from .agent import Agent
from .tools import ToolRegistry

# 自动加载 .env — 从包位置向上查找项目根目录
def _find_project_root() -> Path:
    """从当前文件向上查找包含 .env 的目录"""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / ".env").exists():
            return current
        current = current.parent
    return Path.cwd()

_project_root = _find_project_root()
load_dotenv(_project_root / ".env")

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# AgentProfile — 受 EduClaw / Agent Scaling Law 启发
# ═══════════════════════════════════════════════

@dataclass
class AgentProfile:
    """
    Agent 结构化档案 — 受 Agent Scaling Law (EduClaw) 启发
    能力 = f(角色清晰度, 技能深度, 工具完备度, 运行时能力, 专业知识注入)
    """
    name: str
    role: str                         # 角色定义（如 "教案设计师"）
    description: str                  # 一句话描述
    skills: List[str] = field(default_factory=list)       # 技能列表
    tools: List[str] = field(default_factory=list)        # 工具列表
    pedagogical_depth: int = 1        # 教学深度 1-5
    zpd_enabled: bool = True          # 是否启用 ZPD 自适应
    adaptation_rules: Dict[str, Any] = field(default_factory=dict)  # 自适应规则

    @property
    def profile_richness(self) -> float:
        """Profile 结构丰富度评分 — Agent Scaling Law 核心指标"""
        score = 0.0
        score += min(len(self.role) / 10, 1.0) * 0.2        # 角色清晰度
        score += min(len(self.skills) / 5, 1.0) * 0.25       # 技能深度
        score += min(len(self.tools) / 3, 1.0) * 0.20        # 工具完备度
        score += min(self.pedagogical_depth / 5, 1.0) * 0.20 # 教学深度
        score += (0.15 if self.zpd_enabled else 0.0)         # 自适应能力
        return round(score, 3)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": self.skills,
            "tools": self.tools,
            "pedagogical_depth": self.pedagogical_depth,
            "zpd_enabled": self.zpd_enabled,
            "profile_richness": self.profile_richness,
        }
        if self.adaptation_rules:
            d["adaptation_rules"] = self.adaptation_rules
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# ZPDLevel — 最近发展区层级 (AgentSchool)
# ═══════════════════════════════════════════════

class ZPDLevel(Enum):
    """最近发展区 (Zone of Proximal Development) 层级"""
    INDEPENDENT = "independent"       # 学生能独立完成
    SCAFFOLDED = "scaffolded"         # 需支架式辅助
    GUIDED = "guided"                 # 需教师引导
    UNKNOWN = "unknown"               # 尚未评估


# ═══════════════════════════════════════════════
# StudentProfile — 学生画像 (MAIC Adaptive Engine)
# ═══════════════════════════════════════════════

@dataclass
class StudentProfile:
    """
    学生画像 — 受 MAIC Adaptive Engine 启发
    通过对话式访谈收集，支持 token 级个性化
    """
    name: str
    grade: str = ""                    # 年级
    subject_scores: Dict[str, float] = field(default_factory=dict)  # 各科成绩
    zpd_levels: Dict[str, ZPDLevel] = field(default_factory=dict)   # 各知识点ZPD
    learning_style: str = ""           # 学习风格偏好
    known_points: List[str] = field(default_factory=list)     # 已掌握
    weak_points: List[str] = field(default_factory=list)      # 薄弱点
    misconceptions: List[str] = field(default_factory=list)    # 错误概念
    interaction_history: int = 0       # 交互次数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "grade": self.grade,
            "subject_scores": self.subject_scores,
            "zpd_levels": {k: v.value for k, v in self.zpd_levels.items()},
            "learning_style": self.learning_style,
            "known_points": self.known_points,
            "weak_points": self.weak_points,
            "misconceptions": self.misconceptions,
            "interaction_history": self.interaction_history,
        }


# ═══════════════════════════════════════════════
# Orchestrator — 增强版编排器
# ═══════════════════════════════════════════════

class Orchestrator:
    """
    多 Agent 编排器（2026 增强版）

    新特性：
    - AgentProfile 驱动: 结构化档案管理 Agent 能力 (Agent Scaling Law)
    - ZPD-aware 路由: 根据学生水平自适应分配任务 (AgentSchool)
    - 学生画像: 对话式收集，token 级个性化 (MAIC)
    - 分支管线: 支持 fork-join 并行执行 (LectūraAgents)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen-plus",
    ):
        self.agents: Dict[str, Agent] = {}
        self.profiles: Dict[str, AgentProfile] = {}  # name → AgentProfile
        self.student_pool: Dict[str, StudentProfile] = {}  # name → StudentProfile
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

    # ─── Agent 注册与 Profile ─────────────────

    def register(
        self,
        agent: Agent,
        profile: Optional[AgentProfile] = None,
    ):
        """注册 Agent，可选关联 AgentProfile"""
        agent.configure_llm(self.client)
        agent.model = self.model
        self.agents[agent.name] = agent

        if profile:
            self.profiles[agent.name] = profile
            logger.info(
                f"Agent 注册: {agent.name} | "
                f"Profile 丰富度: {profile.profile_richness:.3f}"
            )
        else:
            logger.info(f"Agent 注册: {agent.name} (无 Profile)")

    def register_all(
        self,
        agents: List[Agent],
        profiles: Optional[Dict[str, AgentProfile]] = None,
    ):
        """批量注册 Agent，可选关联 Profiles"""
        for agent in agents:
            p = profiles.get(agent.name) if profiles else None
            self.register(agent, profile=p)

    def get_agent_with_profile(self, name: str) -> Dict[str, Any]:
        """获取 Agent 及其 Profile 的完整信息"""
        info = {"name": name, "registered": name in self.agents}
        if name in self.profiles:
            info["profile"] = self.profiles[name].to_dict()
        if name in self.agents:
            info["mode"] = self.agents[name].mode
        return info

    def list_profiles(self) -> List[Dict[str, Any]]:
        """列出所有注册 Agent 的 Profile"""
        return [
            {"name": name, **self.profiles[name].to_dict()}
            for name in self.agents
            if name in self.profiles
        ]

    # ─── 学生画像管理 ──────────────────────────

    def register_student(self, profile: StudentProfile):
        """注册学生画像"""
        self.student_pool[profile.name] = profile
        logger.info(f"学生注册: {profile.name}")

    def update_student_zpd(
        self,
        student_name: str,
        topic: str,
        level: ZPDLevel,
    ):
        """更新学生某知识点的 ZPD 层级"""
        if student_name in self.student_pool:
            self.student_pool[student_name].zpd_levels[topic] = level

    def get_student(self, name: str) -> Optional[StudentProfile]:
        return self.student_pool.get(name)

    # ─── ZPD-aware 路由 ────────────────────────

    def route(
        self,
        task: str,
        student: Optional[Union[str, StudentProfile]] = None,
        **context,
    ) -> Dict[str, Any]:
        """
        智能路由（ZPD-aware）

        如果提供了学生信息，优先选择 ZPD 匹配的 Agent；
        否则走原始 LLM 路由逻辑。
        """
        if not self.agents:
            raise RuntimeError("没有注册任何 Agent")

        # 获取学生画像
        student_profile: Optional[StudentProfile] = None
        if isinstance(student, str):
            student_profile = self.student_pool.get(student)
        elif isinstance(student, StudentProfile):
            student_profile = student

        if student_profile:
            context["student_profile"] = student_profile.to_dict()

        agent_names = list(self.agents.keys())

        # 构建路由 prompt
        agent_descs = "\n".join(
            f"- {name}: {self.agents[name].get_system_prompt()[:120]}..."
            for name in agent_names
        )

        zpd_hint = ""
        if student_profile:
            zpd_hint = (
                f"\n学生: {student_profile.name}\n"
                f"薄弱点: {', '.join(student_profile.weak_points[:3])}\n"
                f"已掌握: {', '.join(student_profile.known_points[:3])}\n"
                f"请选择最适合该学生当前水平的 Agent。"
            )

        prompt = f"""以下是一个教学任务，请从可用 Agent 中选择最合适的一个。

任务: {task}
可用 Agent:
{agent_descs}
{zpd_hint}
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
                    logger.info(
                        f"路由: '{task[:40]}...' → {name}"
                        + (f" (学生: {student_profile.name})" if student_profile else "")
                    )
                    result = self.agents[name].run(task, **context)
                    return {"agent": name, "result": result}
        except Exception as e:
            logger.warning(f"自动路由失败: {e}")

        first = list(self.agents.keys())[0]
        result = self.agents[first].run(task, **context)
        return {"agent": first, "result": result}

    # ─── 管线执行（支持分支） ──────────────────

    def pipeline(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        管线执行：支持串行 + 分支并行

        tasks 格式：
        - 普通串行: {"agent": "name", "task": "..."}
        - 分支并行: {"fork": [{"agent": "a", "task": "..."}, {"agent": "b", "task": "..."}],
                      "join": True}
        """
        results = []
        shared_context: Dict[str, Any] = {}

        for item in tasks:
            # ── 分支并行点 ──
            if "fork" in item:
                fork_tasks = item["fork"]
                if not isinstance(fork_tasks, list):
                    results.append({"error": "fork 值必须是列表"})
                    continue

                fork_results = []
                for ft in fork_tasks:
                    agent_name = ft.get("agent")
                    task_desc = ft.get("task", "")
                    if agent_name and agent_name in self.agents:
                        fr = self.agents[agent_name].run(task_desc, **shared_context)
                        fork_results.append({"agent": agent_name, "task": task_desc, "result": fr})
                    else:
                        fork_results.append({"agent": agent_name, "task": task_desc, "error": "未注册"})

                # join: 合并分支结果到上下文
                if item.get("join", True):
                    shared_context["fork_results"] = fork_results
                results.append({"type": "fork", "children": fork_results})
                continue

            # ── 普通串行节点 ──
            agent_name = item.get("agent")
            task_desc = item.get("task", "")

            if agent_name and agent_name in self.agents:
                shared_context["pipeline_results"] = [
                    {"agent": r["agent"], "task": r.get("task", ""), "result": r.get("result", "")}
                    for r in results if "result" in r
                ]
                result = self.agents[agent_name].run(task_desc, **shared_context)
                shared_context["previous_result"] = result
                results.append({"agent": agent_name, "task": task_desc, "result": result})
            else:
                results.append({"agent": agent_name, "task": task_desc, "error": f"Agent '{agent_name}' 未注册"})

        return results

    # ─── 自适应教学推荐 ─────────────────────────

    def recommend_adaptation(
        self,
        student_name: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        根据学生画像和 ZPD 层级推荐教学策略 (MAIC 自适应引擎)
        """
        student = self.student_pool.get(student_name)
        if not student:
            return {"error": f"学生 '{student_name}' 未注册"}

        zpd = student.zpd_levels.get(topic, ZPDLevel.UNKNOWN)
        zpd_map = {
            ZPDLevel.INDEPENDENT: {
                "action": "提供进阶练习",
                "agent": "quiz_generator",
                "difficulty": "advanced",
            },
            ZPDLevel.SCAFFOLDED: {
                "action": "提供支架式讲解+练习",
                "agent": "lesson_planner",
                "difficulty": "intermediate",
            },
            ZPDLevel.GUIDED: {
                "action": "一对一引导教学",
                "agent": "learning_diagnosis",
                "difficulty": "basic",
            },
            ZPDLevel.UNKNOWN: {
                "action": "诊断评估后制定策略",
                "agent": "learning_diagnosis",
                "difficulty": "basic",
            },
        }

        rec = zpd_map[zpd]
        rec["student"] = student_name
        rec["topic"] = topic
        rec["zpd_level"] = zpd.value
        return rec

    # ─── 状态 ──────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """获取编排器完整状态"""
        return {
            "model": self.model,
            "registered_agents": list(self.agents.keys()),
            "agent_count": len(self.agents),
            "profiles_count": len(self.profiles),
            "students_count": len(self.student_pool),
            "avg_profile_richness": (
                sum(p.profile_richness for p in self.profiles.values()) / len(self.profiles)
                if self.profiles else 0.0
            ),
        }

    @staticmethod
    def _env(key: str, default: str = "") -> str:
        return os.getenv(key, default)
