"""
图片识别分析 Agent —— 从图片中提取教育内容并结构化分析
"""

import json
import logging
from typing import Any, Dict, List, Optional

from eduagent.core.agent import Agent

logger = logging.getLogger(__name__)


class ImageAnalyzerAgent(Agent):
    """
    图片识别分析 Agent

    能力：
    - OCR 文字提取（教材页、试卷、板书、笔记等）
    - 学科与知识点自动识别
    - 教育内容结构化分析
    - 教学建议生成

    参数:
        vision_model: 视觉模型名称，默认 qwen-vl-plus
                     可选 qwen-vl-max, qwen-vl-ocr-2025-11-20
    """

    def __init__(self, vision_model: str = "qwen-vl-plus", **kwargs):
        super().__init__(
            name="image_analyzer",
            vision_model=vision_model,
            **kwargs,
        )

    def get_system_prompt(self) -> str:
        return """你是一位教育内容分析专家，擅长从图片中提取和分析教学相关内容。

## 你的能力
- 精确提取图片中的文字内容（OCR），包括手写笔记、印刷教材、板书
- 识别学科分类、适用年级、核心知识点
- 分析内容结构和教学重点
- 评估内容难度，给出教学建议

## 输出规范

根据 mode 参数调整输出详细程度：

### brief 模式 — 仅 OCR 提取
直接输出图片中的文字内容，不做额外分析。保持原文排版结构。
手写内容用「」标注不确定部分。

### standard 模式 — 结构化分析
按以下格式输出：

# 图片内容分析

## 一、文字提取
[从图片中提取的完整文字，保持原文结构]

## 二、学科与知识点
- **学科**：[数学/物理/化学/语文/英语/生物/历史/地理/政治/其他]
- **适用年级**：[小学/初中/高中/大学 × 年级]
- **核心知识点**：
  1. 知识点一
  2. 知识点二

## 三、内容摘要
[用 2-3 句话概括图片核心内容]

### detailed 模式 — 完整教学分析
在 standard 基础上增加：

## 四、知识点拆解
将核心知识点展开为子知识点树状结构，每个节点标注难度(★☆☆~★★★)

## 五、常见误区预警
列出学生在此知识点上常见的 3-5 个理解误区及纠正方法

## 六、教学建议
- 建议教学顺序
- 推荐教学方法（讲授/讨论/练习/探究）
- 配套练习方向

## 注意事项
- 图片不清晰时，标注「⚠️ 图片模糊，以下提取可能不完整」
- 数学公式用 LaTeX 格式输出（如 $y = x^2 + 2x + 1$）
- 表格数据用 Markdown 表格还原
- 无法识别的内容标注「[无法识别]」
"""

    def run(
        self,
        task: str,
        images: Optional[List[str]] = None,
        image_urls: Optional[List[str]] = None,
        **context,
    ) -> str:
        """
        执行图片分析任务

        参数:
            task: 任务描述（如"分析这张试卷的知识点"）
            images: 本地图片文件路径列表
            image_urls: 远程图片 URL 列表
        """
        context["images"] = images or []
        context["image_urls"] = image_urls or []
        return super().run(task, **context)

    def _execute(
        self,
        plan: str,
        task: str,
        context: Dict[str, Any],
    ) -> str:
        """重写执行阶段，有图片时走视觉调用，无图片时走文本调用"""
        images = context.get("images", [])
        image_urls = context.get("image_urls", [])

        system = self.get_system_prompt()
        mode_hint = context.get("mode_instruction", "")

        image_count = len(images) + len(image_urls)
        image_info = ""
        if images:
            image_info += f"\n本地图片: {', '.join(images)}"
        if image_urls:
            image_info += f"\n远程图片: {', '.join(image_urls)}"

        user_prompt = f"""任务: {task}
执行计划: {plan}
输出要求: {mode_hint}
图片数量: {image_count} 张{image_info}

请按照计划分析图片内容，输出最终结果。"""

        if image_count > 0:
            logger.info(
                f"[{self.name}] 使用视觉模型 {self.vision_model} "
                f"分析 {image_count} 张图片"
            )
            return self._call_llm_vision(
                prompt=user_prompt,
                system=system,
                images=images,
                image_urls=image_urls,
            )
        else:
            # 无图片时回退到纯文本调用，可用于分析已有文本描述
            logger.info(f"[{self.name}] 无图片输入，使用纯文本模式")
            return self._call_llm(user_prompt, system=system)

    def _should_reflect(self, result: str) -> bool:
        """图片分析模式的反思策略：detailed 模式始终反思，其他按长度判断"""
        if self.reflection == "always":
            return True
        if self.reflection == "never":
            return False
        if self.mode == "detailed":
            return True  # detailed 模式始终检查质量
        if self.mode == "brief":
            return len(result) < 50  # 太短的 OCR 结果可能需要重试
        # standard: 长度足够就跳过
        return len(result) < 200
