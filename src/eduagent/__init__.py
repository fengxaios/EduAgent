"""
EduAgent — 面向教学场景的轻量级多智能体框架
"""

from eduagent.core import Agent, Orchestrator, Memory, ToolRegistry, tool, Evaluator
from eduagent.core.structured_protocol import AgentMessage, AgentStatus, PipelineReport
from eduagent.agents import (
    LessonPlannerAgent,
    QuizGeneratorAgent,
    KnowledgeMapperAgent,
    ImageAnalyzerAgent,
    ReporterAgent,
)

__version__ = "2.1.0"
__all__ = [
    "Agent",
    "Orchestrator",
    "Memory",
    "ToolRegistry",
    "tool",
    "Evaluator",
    "AgentMessage",
    "AgentStatus",
    "PipelineReport",
    "LessonPlannerAgent",
    "QuizGeneratorAgent",
    "KnowledgeMapperAgent",
    "ImageAnalyzerAgent",
    "ReporterAgent",
]
