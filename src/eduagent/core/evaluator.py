"""
EduAgent 评测框架 —— 对 Agent 输出质量进行自动化评分

使用场景：
    - 回归测试：确保代码改动不影响输出质量
    - 比赛展示：向评委证明 Agent 输出有客观质量保证
    - 开发调试：快速发现 prompt 调整后的退化
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BenchmarkCase:
    """单个评测用例"""
    id: str
    task: str
    agent: str  # lesson_planner / quiz_generator / knowledge_mapper
    min_length: int = 200
    required_sections: List[str] = field(default_factory=list)
    required_keywords: List[str] = field(default_factory=list)


@dataclass
class ScoreReport:
    """单题评分报告"""
    case_id: str
    total: float
    details: Dict[str, Any] = field(default_factory=dict)


# ─── 内置评测数据集 ──────────────────────────────

BENCHMARK_CASES: List[BenchmarkCase] = [
    # ── 教案设计 ──
    BenchmarkCase(
        id="lesson_001",
        task="为高中二年级设计一节「导数与切线」的教案（detailed模式）",
        agent="lesson_planner",
        min_length=500,
        required_sections=[
            "基本信息", "教学目标", "教学重难点",
            "教学过程", "板书设计", "课后作业",
        ],
        required_keywords=["导数", "切线", "斜率", "极限"],
    ),
    BenchmarkCase(
        id="lesson_002",
        task="为初中三年级设计一节「一元二次方程」的教案（standard模式）",
        agent="lesson_planner",
        min_length=300,
        required_sections=[
            "基本信息", "教学目标", "教学重难点",
            "教学过程", "课后作业",
        ],
        required_keywords=["一元二次方程", "判别式", "求根公式"],
    ),
    # ── 习题生成 ──
    BenchmarkCase(
        id="quiz_001",
        task="出5道关于「牛顿第二定律」的分层练习题（difficulty=intermediate）",
        agent="quiz_generator",
        min_length=400,
        required_sections=["基础巩固", "能力提升"],
        required_keywords=["F=ma", "牛顿"],
    ),
    BenchmarkCase(
        id="quiz_002",
        task="出3道关于「化学平衡移动」的基础练习题（difficulty=basic）",
        agent="quiz_generator",
        min_length=200,
        required_sections=["基础巩固"],
        required_keywords=["勒夏特列", "平衡"],
    ),
    # ── 知识点拆解 ──
    BenchmarkCase(
        id="map_001",
        task="拆解「高中生物·遗传与进化」的知识点",
        agent="knowledge_mapper",
        min_length=500,
        required_sections=[
            "知识树", "前置依赖关系", "教学路线建议", "常见误区预警",
        ],
        required_keywords=["遗传", "基因", "染色体", "变异"],
    ),
    BenchmarkCase(
        id="map_002",
        task="拆解「初中物理·电学基础」的知识点",
        agent="knowledge_mapper",
        min_length=400,
        required_sections=[
            "知识树", "前置依赖关系", "教学路线建议", "常见误区预警",
        ],
        required_keywords=["电流", "电压", "电阻", "欧姆定律"],
    ),
]


# ─── 评分维度 ──────────────────────────────────

SCORING_DIMENSIONS = {
    "completeness": {
        "weight": 0.30,
        "description": "是否覆盖所有要求的内容板块",
    },
    "structure": {
        "weight": 0.20,
        "description": "Markdown 结构是否规范、层次清晰",
    },
    "accuracy": {
        "weight": 0.25,
        "description": "知识内容是否正确（关键词覆盖）",
    },
    "actionability": {
        "weight": 0.15,
        "description": "输出是否可直接使用（非空洞套话）",
    },
    "format": {
        "weight": 0.10,
        "description": "格式规范（标题层级、表格、列表）",
    },
}


class Evaluator:
    """
    离线评测器 —— 不依赖 LLM，基于规则评分
    用于快速回归测试和质量把关
    """

    def __init__(self, cases: Optional[List[BenchmarkCase]] = None):
        self.cases = cases or BENCHMARK_CASES

    def score_one(self, case: BenchmarkCase, output: str) -> ScoreReport:
        """对单个输出进行多维度评分"""
        details = {}

        # 1. 完整性：必填章节覆盖率
        section_hits = sum(
            1 for s in case.required_sections if s in output
        )
        section_score = (
            section_hits / len(case.required_sections) * 100
            if case.required_sections else 100
        )
        details["sections_found"] = section_hits
        details["sections_required"] = len(case.required_sections)
        details["section_coverage"] = round(section_score, 1)

        # 2. 结构规范：检查 Markdown 标题层级
        h2_count = len(re.findall(r'^##\s', output, re.MULTILINE))
        h3_count = len(re.findall(r'^###\s', output, re.MULTILINE))
        table_count = len(re.findall(r'^\|.*\|$', output, re.MULTILINE))
        structure_score = min(100, h2_count * 12 + h3_count * 6 + table_count * 5)
        details["h2_count"] = h2_count
        details["h3_count"] = h3_count
        details["table_rows"] = table_count

        # 3. 准确性：关键词覆盖率
        keyword_hits = sum(
            1 for kw in case.required_keywords if kw in output
        )
        keyword_score = (
            keyword_hits / len(case.required_keywords) * 100
            if case.required_keywords else 100
        )
        details["keywords_found"] = keyword_hits
        details["keywords_required"] = len(case.required_keywords)
        details["keyword_coverage"] = round(keyword_score, 1)

        # 4. 可落地性：长度 + 内容密度
        length = len(output)
        length_score = min(100, length / case.min_length * 100)
        # 检查是否有空洞套话
        buzzword_count = sum(
            1 for bw in ["贯彻落实", "高度重视", "充分认识", "大力推进"]
            if bw in output
        )
        actionability_score = max(0, length_score - buzzword_count * 10)
        details["length"] = length
        details["buzzword_count"] = buzzword_count

        # 5. 格式规范
        has_title = bool(re.match(r'^#\s', output))
        has_list = bool(re.search(r'^\s*[-*]\s', output, re.MULTILINE))
        format_score = (has_title * 40 + has_list * 30 + min(30, table_count * 5))
        details["has_title"] = has_title
        details["has_list"] = has_list

        # 加权总分
        total = (
            SCORING_DIMENSIONS["completeness"]["weight"] * section_score +
            SCORING_DIMENSIONS["structure"]["weight"] * structure_score +
            SCORING_DIMENSIONS["accuracy"]["weight"] * keyword_score +
            SCORING_DIMENSIONS["actionability"]["weight"] * actionability_score +
            SCORING_DIMENSIONS["format"]["weight"] * format_score
        )
        details["dimension_scores"] = {
            "completeness": round(section_score, 1),
            "structure": round(structure_score, 1),
            "accuracy": round(keyword_score, 1),
            "actionability": round(actionability_score, 1),
            "format": round(format_score, 1),
        }

        return ScoreReport(case_id=case.id, total=round(total, 1), details=details)

    def evaluate(
        self,
        run_fn: Callable[[str, str], str],
        case_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        批量评测

        参数:
            run_fn: (task, agent) -> output 的回调函数
            case_ids: 指定要评测的用例 ID，None 表示全部
        """
        target_cases = self.cases
        if case_ids:
            target_cases = [c for c in self.cases if c.id in case_ids]

        reports: List[ScoreReport] = []
        for case in target_cases:
            try:
                output = run_fn(case.task, case.agent)
                report = self.score_one(case, output)
                reports.append(report)
            except Exception as e:
                reports.append(ScoreReport(
                    case_id=case.id, total=0,
                    details={"error": str(e)},
                ))

        # 汇总统计
        scores = [r.total for r in reports]
        avg_score = sum(scores) / len(scores) if scores else 0
        pass_count = sum(1 for s in scores if s >= 60)

        return {
            "total_cases": len(reports),
            "pass_count": pass_count,
            "pass_rate": round(pass_count / len(reports) * 100, 1) if reports else 0,
            "avg_score": round(avg_score, 1),
            "min_score": round(min(scores), 1) if scores else 0,
            "max_score": round(max(scores), 1) if scores else 0,
            "reports": [
                {
                    "case_id": r.case_id,
                    "score": r.total,
                    "details": r.details,
                }
                for r in reports
            ],
        }

    def render_report(self, results: Dict[str, Any]) -> str:
        """将评测结果渲染为 Markdown 报告"""
        lines = [
            "# EduAgent 评测报告",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 评测用例数 | {results['total_cases']} |",
            f"| 通过数 (≥60) | {results['pass_count']} |",
            f"| 通过率 | {results['pass_rate']}% |",
            f"| 平均分 | {results['avg_score']} |",
            f"| 最低分 | {results['min_score']} |",
            f"| 最高分 | {results['max_score']} |",
            "",
            "## 各维度得分",
            "",
            "| 维度 | 权重 | 说明 |",
            "|------|------|------|",
        ]
        for dim, cfg in SCORING_DIMENSIONS.items():
            lines.append(f"| {dim} | {cfg['weight']:.0%} | {cfg['description']} |")

        lines += [
            "",
            "## 逐题详情",
            "",
        ]
        for r in results["reports"]:
            details = r.get("details", {})
            dims = details.get("dimension_scores", {})
            lines.append(f"### {r['case_id']} — {r['score']}分")
            lines.append(f"- 长度: {details.get('length', 'N/A')} 字")
            lines.append(f"- 各维度: {dims}")
            if "error" in details:
                lines.append(f"- ❌ 错误: {details['error']}")
            lines.append("")

        return "\n".join(lines)
