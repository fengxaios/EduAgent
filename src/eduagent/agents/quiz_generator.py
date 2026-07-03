"""
习题生成 Agent —— 根据知识点自动生成分层练习题
"""

from typing import Any, Dict, Literal

from eduagent.core.agent import Agent

DifficultyType = Literal["basic", "intermediate", "advanced", "all"]

DIFFICULTY_CONFIG = {
    "basic": {
        "sections": ["基础巩固"],
        "ratio": "全部为基础题",
        "count": "3-4 道",
        "instruction": "只出基础巩固题，适合刚学完概念的课堂练习。",
    },
    "intermediate": {
        "sections": ["基础巩固", "能力提升"],
        "ratio": "基础 50% / 提高 50%",
        "count": "5-6 道",
        "instruction": "出基础+提高题，适合课后作业或阶段测验。",
    },
    "advanced": {
        "sections": ["能力提升", "拓展挑战"],
        "ratio": "提高 60% / 拓展 40%",
        "count": "4-5 道",
        "instruction": "出提高+拓展题，适合竞赛预备或高水平学生。",
    },
    "all": {
        "sections": ["基础巩固", "能力提升", "拓展挑战"],
        "ratio": "基础 50% / 提高 35% / 拓展 15%",
        "count": "6-8 道",
        "instruction": "三层难度全覆盖，适合单元复习或综合练习。",
    },
}


class QuizGeneratorAgent(Agent):
    """
    习题生成 Agent
    能力：输入知识点/章节，输出分层练习题（基础→提高→拓展）
    支持：选择题、填空题、解答题、证明题

    参数:
        difficulty: basic / intermediate / advanced / all
    """

    def __init__(self, difficulty: DifficultyType = "all", **kwargs):
        super().__init__(name="quiz_generator", **kwargs)
        self.difficulty: DifficultyType = difficulty

    def run(self, task: str, **context) -> str:
        """注入难度配置后执行"""
        config = DIFFICULTY_CONFIG[self.difficulty]
        context["difficulty"] = self.difficulty
        context["difficulty_config"] = config
        return super().run(task, **context)

    def get_system_prompt(self) -> str:
        template = self._get_template_hint()
        return f"""你是一位经验丰富的命题专家，擅长设计分层练习题。

## 你的能力
- 根据知识点生成难度递进的习题
- 覆盖多种题型（选择、填空、解答、证明）
- 每道题附带参考答案和分步解析
- 题目难度按用户指定的层级生成

## 参考模板
{template}

## 输出规范

# {{知识点}} - 分层练习题

> 核心知识点回顾（2-3句概括关键公式/定理）

## 一、基础巩固（建议用时：X分钟）
### 1. 【选择题】题目
A. ... B. ... C. ... D. ...
> 答案：X
> 解析：分步说明
> ⚠️ 易错点：...

### 2. 【填空题】题目
> 答案：XXX
> 解析：分步说明

## 二、能力提升（建议用时：X分钟）
### 3. 【解答题】题目
> 答案：...
> 解析：分步推导

## 三、拓展挑战（建议用时：X分钟）
### 4. 【综合题/证明题】题目
> 答案：...
> 解析：分步推导，体现综合运用

## 注意事项
- 严格按照用户指定的难度层级和题目数量生成
- 选择题必须有 4 个选项，干扰项要有迷惑性
- 解答题给出完整分步推导，标注关键步骤
- 数学公式使用 LaTeX 格式（$...$ 或 $$...$$）
- 每道题必须标注易错点（⚠️ 易错点）"""

    def _get_template_hint(self) -> str:
        try:
            tmpl = self.load_template("quiz_template")
            return f"模板参考:\n{tmpl}"
        except FileNotFoundError:
            return ""
