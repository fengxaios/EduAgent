"""
Reporter Agent —— 自动汇总 Pipeline 输出生成结构化报告

受 PentAGI 自动报告生成机制启发。
"""

from typing import Any, Dict, List

from eduagent.core.agent import Agent
from eduagent.core.structured_protocol import (
    AgentMessage,
    AgentStatus,
    PipelineReport,
)


class ReporterAgent(Agent):
    """
    报告汇总 Agent

    能力：
    - 接收 Pipeline 中所有 Agent 的输出
    - 提取摘要、计算置信度
    - 生成结构化 Markdown 报告
    - 进行跨 Agent 交叉分析

    这是 PentAGI 式"执行完自动出报告"的 EduAgent 实现。
    """

    def __init__(self, **kwargs):
        super().__init__(name="reporter", **kwargs)

    def get_system_prompt(self) -> str:
        return """你是一位专业的技术报告撰写专家。

## 你的能力
- 汇总多个 Agent 的输出，生成结构化报告
- 提取每个输出的核心摘要（≤100字）
- 评估每个输出的置信度（1-10分）
- 进行跨输出交叉分析
- 输出可直接交付的 Markdown 报告

## 输出规范
按以下结构输出：
1. 执行概览
2. 各 Agent 输出与评估
3. 交叉分析
4. 建议与下一步"""

    def build_report(
        self,
        pipeline_name: str,
        pipeline_results: List[Dict[str, Any]],
    ) -> PipelineReport:
        """
        从 Pipeline 原始结果构建结构化报告

        这是核心方法 — 兼容现有 Orchestrator.pipeline() 输出格式
        """
        report = PipelineReport(pipeline_name=pipeline_name)

        for item in pipeline_results:
            agent_name = item.get("agent", "unknown")
            task = item.get("task", "")

            if "error" in item:
                msg = AgentMessage(
                    agent_name=agent_name,
                    task=task,
                    status=AgentStatus.FAILED,
                    summary=f"执行失败: {item['error'][:100]}",
                    artifact=item.get("error", ""),
                    confidence=0.0,
                    metadata={"error": item["error"]},
                )
            else:
                result = item.get("result", "")
                # 用启发式方法评估置信度
                confidence = self._estimate_confidence(result)
                summary = self._extract_summary(result)

                msg = AgentMessage(
                    agent_name=agent_name,
                    task=task,
                    status=AgentStatus.SUCCESS,
                    artifact=result,
                    summary=summary,
                    confidence=confidence,
                    metadata={
                        "result_length": len(result),
                        "has_structure": "##" in result,
                    },
                )

            report.messages.append(msg)

        return report

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """
        启发式置信度评估（不需要额外 LLM 调用）

        维度：长度 + 结构完整性 + 内容密度
        """
        score = 0.0
        # 长度足够（>500字 = 0.3）
        if len(text) > 500:
            score += 0.3
        elif len(text) > 200:
            score += 0.15
        # 有 Markdown 结构（标题 + 表格/列表 = 0.3）
        if "##" in text:
            score += 0.15
        if "|" in text:
            score += 0.1
        if "- " in text:
            score += 0.05
        # 没有空洞套话 = 0.2
        buzzwords = ["贯彻落实", "高度重视", "大力推进", "充分认识"]
        if not any(bw in text for bw in buzzwords):
            score += 0.2
        # 内容密度（非空行占比 > 0.5 = 0.2）
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        total_lines = len(text.split("\n"))
        if total_lines > 0 and len(lines) / total_lines > 0.5:
            score += 0.2

        return min(score, 1.0)

    @staticmethod
    def _extract_summary(text: str, max_len: int = 100) -> str:
        """从输出中提取简短摘要"""
        # 取第一个非空、有意义的内容行
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # 跳过标题行
        for line in lines:
            if line.startswith("#"):
                continue
            if len(line) > 10:
                summary = line[:max_len]
                return summary + ("..." if len(line) > max_len else "")
        return text[:max_len] + ("..." if len(text) > max_len else "")
