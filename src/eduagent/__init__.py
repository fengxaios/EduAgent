"""
EduAgent — 面向教学场景的轻量级多智能体框架
"""

from eduagent.core import Agent, Orchestrator, Memory, ToolRegistry, tool, Evaluator
from eduagent.agents import (
    LessonPlannerAgent,
    QuizGeneratorAgent,
    KnowledgeMapperAgent,
    ImageAnalyzerAgent,
)

__version__ = "0.2.0"
__all__ = [
    "Agent",
    "Orchestrator",
    "Memory",
    "ToolRegistry",
    "tool",
    "Evaluator",
    "LessonPlannerAgent",
    "QuizGeneratorAgent",
    "KnowledgeMapperAgent",
    "ImageAnalyzerAgent",
]
