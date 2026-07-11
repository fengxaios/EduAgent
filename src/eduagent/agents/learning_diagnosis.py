"""
学习诊断 Agent — 学生端反馈诊断，补齐教学闭环最后一环

能力：
  1. 错误类型智能分类 — 7 类标准错误
  2. 薄弱知识点定位 — 跨题目分析，评估掌握度(%)
  3. 个性化补救方案 — 短期靶向练习 + 中期巩固 + 学习策略建议
  4. 掌握度等级 — ✅已掌握 / 📖基本掌握 / ⚠️薄弱 / 🔴严重薄弱
  5. 3 种输出模式 — brief / standard（默认）/ detailed

Pipeline 兼容 — 可接入 Orchestrator.pipeline()，接收上游 QuizGenerator 的输出
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from eduagent.core.agent import Agent

logger = logging.getLogger(__name__)

# ── 错误类型枚举 ──────────────────────────────────

ERROR_TYPES = {
    "concept_confusion": {
        "label": "概念混淆",
        "description": "对知识点核心概念理解不清，张冠李戴",
        "example": "把极限和连续混为一谈",
        "priority": "🔴 高",
    },
    "calculation_error": {
        "label": "计算失误",
        "description": "计算过程中出现算术或代数错误",
        "example": "符号错误、运算顺序错误",
        "priority": "🟡 中",
    },
    "careless_reading": {
        "label": "审题粗心",
        "description": "未仔细阅读题目条件或要求就作答",
        "example": "看错条件、漏掉关键信息",
        "priority": "🟢 低",
    },
    "wrong_method": {
        "label": "方法不当",
        "description": "选用了错误的解题方法或公式",
        "example": "该用分部积分却用了换元法",
        "priority": "🔴 高",
    },
    "logic_flaw": {
        "label": "逻辑缺陷",
        "description": "推理链条断裂、因果倒置等逻辑问题",
        "example": "证明题步骤跳跃、缺乏依据",
        "priority": "🔴 高",
    },
    "expression_issue": {
        "label": "表达不规范",
        "description": "答案正确但书写格式、步骤表述不标准",
        "example": "缺少单位、推导跳步、公式书写错误",
        "priority": "🟢 低",
    },
    "prerequisite_gap": {
        "label": "前置缺失",
        "description": "因前置知识点未掌握导致当前题目无法解答",
        "example": "不会三角函数导致微积分相关题目出错",
        "priority": "🔴 高",
    },
}

MASTERY_LEVELS = {
    (80, 101): ("✅ 已掌握", "该知识点掌握扎实，可进入下一阶段"),
    (60, 80):  ("📖 基本掌握", "基本理解但需巩固，建议适量练习"),
    (40, 60):  ("⚠️ 薄弱", "部分理解但存在明显漏洞，需重点攻克"),
    (0, 40):   ("🔴 严重薄弱", "几乎未掌握，建议从头复习"),
}


def get_mastery_level(score: float) -> tuple[str, str]:
    """根据得分率返回 (等级标签, 行动建议)"""
    for (lo, hi), (label, advice) in MASTERY_LEVELS.items():
        if lo <= score < hi:
            return label, advice
    return "❓ 未知", ""


class LearningDiagnosisAgent(Agent):
    """
    学习诊断 Agent

    输入：学生答题情况 + 知识点
    输出：错误分类 → 薄弱点定位 → 个性化补救方案

    参数:
        mode: brief / standard / detailed
        student_name: 学生姓名（可选）
    """

    def __init__(
        self,
        mode: Literal["brief", "standard", "detailed"] = "standard",
        student_name: str = "",
        **kwargs,
    ):
        super().__init__(name="learning_diagnosis", mode=mode, **kwargs)
        self.student_name = student_name

    def run(
        self,
        task: str,
        student_answers: Optional[List[Dict[str, Any]]] = None,
        student: str = "",
        **context,
    ) -> str:
        """
        执行诊断

        Args:
            task: 诊断任务描述
            student_answers: 学生答题列表
                [{"question": "...", "student_answer": "...",
                  "correct_answer": "...", "knowledge_point": "..."}]
            student: 学生姓名
            context: 上游 Agent 传递的上下文（如 QuizGenerator 的输出）
        """
        # 从 context 中提取学生答题数据
        if student_answers is None:
            prev = context.get("previous_result", context.get("quiz_result", ""))
            student_answers = self._extract_answers(prev)

        # 无答题数据时的兜底处理
        if not student_answers:
            logger.warning(
                f"[{self.name}] 未收到学生答题数据，将生成基于知识点的通用诊断"
            )
            context["no_data_warning"] = (
                "⚠️ 未收到具体的学生答题数据，请基于知识点本身给出该章节"
                "常见的薄弱点和易错点分析，而非针对特定学生的诊断。"
            )

        context["error_types"] = ERROR_TYPES
        context["mastery_levels"] = MASTERY_LEVELS
        context["student_answers"] = student_answers
        context["student"] = student or self.student_name or "学生"

        return super().run(task, **context)

    def get_system_prompt(self) -> str:
        mode_instruction = {
            "brief": "请用精简格式输出（约30行），只保留核心诊断结论和Top3薄弱点，省略详细分析和示例。",
            "standard": "请用标准格式输出（约60行），包含完整诊断分析、所有薄弱点和补救建议。",
            "detailed": "请详尽展开输出（约100行），包含逐题分析、详细错误归因、多层次补救方案和学习策略建议。",
        }.get(self.mode, "")

        return f"""你是一位资深的教育诊断专家，擅长分析学生答题情况并给出精准的诊断报告和补救方案。

## 你的能力
- 根据学生答题数据，精准定位薄弱知识点
- 按 7 类标准错误类型进行分类（概念混淆/计算失误/审题粗心/方法不当/逻辑缺陷/表达不规范/前置缺失）
- 评估每个知识点的掌握程度（%），给出等级标签
- 制定个性化补救方案（短期靶向练习 + 中期巩固 + 学习策略建议）

## 7 类错误类型
1. 🔴 概念混淆 — 对知识点核心概念理解不清，张冠李戴
2. 🟡 计算失误 — 计算过程中出现算术或代数错误
3. 🟢 审题粗心 — 未仔细阅读题目条件或要求就作答
4. 🔴 方法不当 — 选用了错误的解题方法或公式
5. 🔴 逻辑缺陷 — 推理链条断裂、因果倒置
6. 🟢 表达不规范 — 书写格式、步骤表述不标准
7. 🔴 前置缺失 — 因前置知识点未掌握导致无法解答

## 掌握度等级
- ✅ 已掌握 (≥80%) — 可进入下一阶段
- 📖 基本掌握 (60-79%) — 需适量巩固练习
- ⚠️ 薄弱 (40-59%) — 存在明显漏洞，需重点攻克
- 🔴 严重薄弱 (<40%) — 建议从头复习

## 输出格式

# 学习诊断报告 — {{知识点/章节}}

> 学生：{{姓名}} | 诊断时间：{{日期}} | 分析题目数：{{N}}道

## 一、总体评估

| 指标 | 数值 |
|------|------|
| 正确率 | X/Y = Z% |
| 掌握度等级 | {{等级标签}} |
| 主要错误类型 | {{Top 2-3 类型}} |
| 建议优先级 | {{从最薄弱开始}} |

## 二、逐题诊断

### 第 N 题：{{题目摘要}}

- **学生作答**：...
- **正确答案**：...
- **错误类型**：{{类型标签}}
- **错误分析**：1-2句话说明为什么会犯这个错误
- **涉及知识点**：...
- **补救建议**：具体可操作的练习建议

## 三、薄弱知识点总览

| 知识点 | 掌握度 | 等级 | 错题数 | 建议 |
|--------|--------|------|--------|------|
| ... | X% | ⚠️ | N/总 | ... |

## 四、个性化补救方案

### 🎯 短期（本周）
1. **靶向练习**：
   - ...
2. **重点回顾**：
   - ...

### 📋 中期（本月）
1. **巩固计划**：
   - ...
2. **学习方法建议**：
   - ...

## 五、学习策略建议
- ...
- ...

{mode_instruction}

## 特殊情况处理
- 如果上下文中带有 "no_data_warning" 字段，说明没有具体的学生答题数据
- 此时应生成该章节/知识点的**通用薄弱点分析**（而非针对特定学生的诊断）
- 列出该章节最常见的 5-8 个易错点、典型错误类型和预防建议

## 注意事项
- 诊断要具体到每个错误的知识点层面，不要笼统
- 补救方案要可执行，给出具体的练习方向和数量
- 数学公式使用 LaTeX 格式
- 语气鼓励但不虚假，真实指出问题但给出解决路径"""

    # ── 辅助方法 ──────────────────────────────────

    def _extract_answers(self, raw: Any) -> List[Dict[str, Any]]:
        """从上游输出中提取学生答题数据"""
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            # 尝试解析 JSON
            import json
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return data.get("answers", data.get("student_answers", []))
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    f"[{self.name}] 上游输出非 JSON 格式，无法自动提取答题数据 "
                    f"(前100字符): {str(raw)[:100]}"
                )
        if isinstance(raw, dict):
            return raw.get("answers", raw.get("student_answers", []))
        return []

    def diagnose_batch(
        self,
        answers: List[Dict[str, Any]],
        knowledge_area: str = "",
    ) -> str:
        """
        批量诊断快捷方法

        Args:
            answers: 学生答题列表
            knowledge_area: 知识领域名称

        Returns:
            诊断报告文本
        """
        if not self.client:
            # 离线模式：基于数据做本地统计分析
            return self._offline_analysis(answers, knowledge_area)

        task = f"诊断{knowledge_area or '当前'}章节的学生答题情况"
        return self.run(task, student_answers=answers)

    def _offline_analysis(
        self,
        answers: List[Dict[str, Any]],
        knowledge_area: str = "",
    ) -> str:
        """离线模式：纯本地统计分析，不调用 LLM"""
        if not answers:
            return (
                "# 学习诊断报告\n\n"
                "> ⚠️ 未收到答题数据，无法生成诊断。\n\n"
                "请通过 `student_answers` 参数传入学生答题列表，格式：\n"
                "```python\n"
                '[{"question": "...", "student_answer": "...", '
                '"correct_answer": "...", "knowledge_point": "..."}]\n'
                "```\n\n"
                "或配置 LLM API Key 后使用在线诊断模式。"
            )

        total = len(answers)
        correct = sum(
            1 for a in answers
            if str(a.get("student_answer", "")).strip()
            == str(a.get("correct_answer", "")).strip()
        )
        accuracy = correct / total * 100 if total > 0 else 0
        label, advice = get_mastery_level(accuracy)

        # 按知识点统计
        kp_stats: Dict[str, Dict[str, int]] = {}
        for a in answers:
            kp = a.get("knowledge_point", "未分类")
            if kp not in kp_stats:
                kp_stats[kp] = {"total": 0, "correct": 0}
            kp_stats[kp]["total"] += 1
            if str(a.get("student_answer", "")).strip() == str(a.get("correct_answer", "")).strip():
                kp_stats[kp]["correct"] += 1

        lines = [
            f"# 学习诊断报告 — {knowledge_area or '综合'}",
            "",
            f"> 诊断模式：离线统计 | 分析题目数：{total}道",
            "",
            "## 一、总体评估",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 正确率 | {correct}/{total} = {accuracy:.1f}% |",
            f"| 掌握度等级 | {label} |",
            f"| 建议 | {advice} |",
            "",
            "## 二、知识点掌握度",
            "",
            "| 知识点 | 正确 | 总数 | 掌握度 | 等级 |",
            "|--------|------|------|--------|------|",
        ]

        for kp, stats in sorted(kp_stats.items()):
            rate = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
            lvl, _ = get_mastery_level(rate)
            lines.append(
                f"| {kp} | {stats['correct']} | {stats['total']} | {rate:.0f}% | {lvl} |"
            )

        lines.extend([
            "",
            "## 三、下一步",
            "",
            f"- {advice}",
            "- 💡 配置 LLM API Key 后可使用在线诊断，获得详细错误归因和个性化补救方案",
            "- 💡 在线模式命令：`python -m eduagent diagnosis \"{knowledge_area or '章节'}\"`",
        ])

        return "\n".join(lines)
