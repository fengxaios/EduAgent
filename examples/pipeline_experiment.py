"""
实验：PentAGI 式结构化通信 + Pipeline 报告自动生成

在这个实验中，我们验证两个从 PentAGI 学到的模式：

1. **结构化通信协议**
   Agent 间传递 AgentMessage 而非纯文本，
   每条消息包含：状态、产物、置信度、元数据。

2. **Pipeline 自动报告生成**
   ReporterAgent 接收所有 Pipeline 输出，
   生成包含交叉分析的结构化 Markdown 报告。

运行方式:
    python examples/pipeline_experiment.py

前提:
    已配置 .env 中的 DASHSCOPE_API_KEY
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from eduagent import (
    Orchestrator,
    KnowledgeMapperAgent,
    LessonPlannerAgent,
    QuizGeneratorAgent,
    ReporterAgent,
    AgentMessage,
    AgentStatus,
    PipelineReport,
)


def experiment_1_structured_protocol():
    """实验 1: 结构化通信协议的基本使用"""
    print("=" * 60)
    print("实验 1: 结构化通信协议")
    print("=" * 60)

    # 模拟一个 Agent 输出
    msg = AgentMessage(
        agent_name="knowledge_mapper",
        task="拆解「定积分」知识点",
        status=AgentStatus.SUCCESS,
        artifact="## 知识树\n- 定积分概念 (★☆☆)\n- 牛顿-莱布尼茨公式 (★★☆)\n- 定积分应用 (★★★)",
        summary="将定积分拆解为3个层级子知识点，覆盖基础到应用",
        confidence=0.85,
        metadata={"knowledge_count": 3, "max_depth": 2},
    )

    print(f"\n序列化 (JSON):")
    print(f"  {msg.to_json()[:200]}...")
    print(f"\n反序列化验证:")
    msg2 = AgentMessage.from_dict(msg.to_dict())
    assert msg2.agent_name == msg.agent_name
    assert msg2.status == msg.status
    print(f"  ✅ 序列化/反序列化一致")

    # 模拟 Pipeline 报告
    report = PipelineReport(pipeline_name="定积分教学设计")
    report.messages = [
        msg,
        AgentMessage(
            agent_name="lesson_planner",
            task="生成定积分教案",
            status=AgentStatus.SUCCESS,
            artifact="## 定积分教案\n### 教学目标...\n### 教学过程...",
            summary="生成45分钟定积分标准教案，含三维目标和完整教学过程",
            confidence=0.90,
        ),
        AgentMessage(
            agent_name="quiz_generator",
            task="出5道定积分习题",
            status=AgentStatus.SUCCESS,
            artifact="## 定积分分层练习\n### 基础巩固\n1. 选择题...\n### 能力提升\n3. 解答题...",
            summary="生成5道分层习题，覆盖基础巩固和能力提升",
            confidence=0.78,
        ),
    ]

    print(f"\n报告统计:")
    print(f"  成功率: {report.success_rate:.0%}")
    print(f"  平均置信度: {report.total_confidence:.2f}")
    print(f"  Agent 数: {len(report.messages)}")

    # 生成 Markdown 报告
    md_report = report.to_markdown()
    lines_count = len(md_report.split("\n"))
    print(f"\nMarkdown 报告:")
    print(f"  总行数: {lines_count}")
    print(f"  包含交叉分析: {'交叉分析' in md_report}")

    # 保存报告
    output_path = Path(__file__).resolve().parent.parent / "pipeline_report_demo.md"
    output_path.write_text(md_report, encoding="utf-8")
    print(f"\n  📄 报告已保存: {output_path}")


def experiment_2_reporter_agent():
    """实验 2: ReporterAgent 自动汇总 Pipeline 输出"""
    print("\n" + "=" * 60)
    print("实验 2: ReporterAgent 自动汇总（启发式模式）")
    print("=" * 60)

    reporter = ReporterAgent()

    # 模拟 Pipeline 完成后的原始数据
    mock_results = [
        {
            "agent": "knowledge_mapper",
            "task": "拆解牛顿力学知识点",
            "result": "## 一、知识树\n牛顿力学\n├── 牛顿第一定律 (★★☆) [讲授]\n│   ├── 惯性概念 (★☆☆)\n│   └── 力与运动状态 (★★☆)\n├── 牛顿第二定律 (★★★) [讲授+练习]\n│   ├── F=ma (★★☆)\n│   └── 多体问题 (★★★)\n├── 牛顿第三定律 (★★☆) [讲授]\n└── 牛顿力学综合应用 (★★★) [探究]\n\n## 二、前置依赖关系\n- 矢量运算 → 牛顿第二定律\n- 牛顿第一定律 → 牛顿第二定律\n- 匀变速直线运动 → 牛顿第二定律应用\n\n## 三、教学路线建议\n### 路径一：标准路径\n矢量基础 → 牛顿第一定律 → 牛顿第二定律 → 牛顿第三定律 → 综合\n\n### 路径二：快速路径\n跳过矢量细节，直接用标量形式讲授F=ma\n\n### 路径三：深度学习路径\n增加微积分方法推导、多体问题、非惯性系\n\n## 四、常见误区预警\n1. **力是维持运动的原因**：学生常认为没有力物体就会停下来 → 用气垫导轨实验纠正\n2. **作用力与反作用力抵消**：学生误以为作用力反作用力作用在同一物体上 → 强调作用对象不同\n3. **加速度与速度方向混淆**：学生常常搞混 → 用矢量图直观展示",
        },
        {
            "agent": "lesson_planner",
            "task": "生成牛顿第二定律一节教案",
            "result": "## 牛顿第二定律 - 教学设计\n\n## 一、基本信息\n- 适用学段：高中一年级\n- 课时安排：1课时（45分钟）\n- 课型：新授课\n\n## 二、教学目标\n### 知识与技能\n- 理解牛顿第二定律的内容及公式 F=ma\n- 能运用牛顿第二定律解决简单的力学问题\n\n### 过程与方法\n- 通过实验探究力、质量、加速度的关系\n- 培养控制变量法的科学思维\n\n### 情感态度与价值观\n- 体会物理学中简洁优美的数学表达\n- 培养严谨的科学态度\n\n## 三、教学重难点\n- 重点：牛顿第二定律的公式理解和基本应用\n- 难点：加速度与合外力的瞬时对应关系\n- 突破策略：DIS实验 + 实时数据采集，直观展示 a-F 和 a-m 关系\n\n## 四、教学过程\n| 环节 | 内容要点 | 时长 | 师生活动 |\n|------|----------|------|----------|\n| 导入 | 回顾牛顿第一定律，设问：力如何影响运动？ | 3min | 教师提问，学生回顾 |\n| 实验探究 | DIS实验：控制变量法测 a-F、a-m 关系 | 15min | 分组实验，教师指导 |\n| 数据分析 | 归纳实验规律，得出 F=ma | 10min | 师生共同推导 |\n| 巩固练习 | 例题讲解 + 变式训练 | 12min | 学生板演，教师点评 |\n| 小结 | 回顾公式、单位和适用范围 | 5min | 教师总结 |\n\n## 五、板书设计\n（左）牛顿第二定律 F=ma\n（中）实验数据表格\n（右）例题步骤\n\n## 六、课后作业\n1. 课本P78 1-3题\n2. 思考：如果力不是恒力，F=ma 还成立吗？",
        },
        {
            "agent": "quiz_generator",
            "task": "出5道牛顿第二定律练习题",
            "result": "## 牛顿第二定律 - 分层练习题\n\n## 一、基础巩固\n### 1. 【选择题】一个质量为2kg的物体受到10N的合外力作用，其加速度为：\nA. 2 m/s²\nB. 5 m/s²  \nC. 10 m/s²\nD. 20 m/s²\n> 答案：B\n> 解析：由F=ma，a=F/m=10/2=5 m/s²\n> ⚠️ 易错点：注意单位换算，合外力与加速度同向\n\n### 2. 【填空题】质量为5kg的物体，在20N水平力作用下沿光滑水平面运动，加速度为___m/s²\n> 答案：4\n> 解析：光滑水平面→无摩擦，a=F/m=20/5=4 m/s²\n\n## 二、能力提升\n### 3. 【解答题】如图，质量为3kg的物体受到两个力的作用：F₁=12N向右，F₂=6N向左。求物体的加速度大小和方向。\n> 答案：a=2 m/s²，方向向右\n> 解析：F合=F₁-F₂=12-6=6N，a=F合/m=6/3=2 m/s²，方向与合外力同向\n\n### 4. 【解答题】一辆质量为1000kg的汽车，从静止开始以恒定牵引力2000N加速，受到的阻力为500N。求：\n(1) 汽车的加速度\n(2) 经过10s后的速度\n> 答案：(1) a=1.5 m/s²  (2) v=15 m/s\n> 解析：(1) F合=2000-500=1500N，a=F合/m=1500/1000=1.5 m/s²\n> (2) v=v₀+at=0+1.5×10=15 m/s\n> ⚠️ 易错点：不要忘记减阻力\n\n## 三、拓展挑战\n### 5. 【综合题】质量为m的物块放在倾角为θ的斜面上，斜面光滑。求：\n(1) 物块沿斜面下滑的加速度\n(2) 若斜面粗糙，动摩擦因数为μ，加速度为多少？\n> 答案：(1) a=gsinθ  (2) a=g(sinθ-μcosθ)\n> 解析：\n> (1) 沿斜面方向：mgsinθ=ma → a=gsinθ\n> (2) 加摩擦力：mgsinθ-μmgcosθ=ma → a=g(sinθ-μcosθ)\n> ⚠️ 易错点：摩擦力方向与运动方向相反；需先判断sinθ > μcosθ才能下滑",
        },
    ]

    # ReporterAgent 构建报告
    report = reporter.build_report(
        pipeline_name="牛顿力学教学设计流水线",
        pipeline_results=mock_results,
    )

    print(f"\nPipeline 报告概览:")
    print(f"  Agent 数量: {len(report.messages)}")
    print(f"  成功率: {report.success_rate:.0%}")
    print(f"  平均置信度: {report.total_confidence:.2f}")

    for msg in report.messages:
        print(f"\n  📌 {msg.agent_name}")
        print(f"     状态: {msg.status}")
        print(f"     置信度: {msg.confidence:.0%}")
        print(f"     摘要: {msg.summary[:60]}...")
        print(f"     产物长度: {len(msg.artifact)} 字")

    # 生成完整 Markdown 报告
    md_report = report.to_markdown()
    report_path = (
        Path(__file__).resolve().parent.parent / "pipeline_report_newton.md"
    )
    report_path.write_text(md_report, encoding="utf-8")
    print(f"\n  📄 完整报告已保存: {report_path}")


def experiment_3_comparison():
    """实验 3: 有无结构化协议的效果对比"""
    print("\n" + "=" * 60)
    print("实验 3: 效果对比 — 结构化 vs 纯文本")
    print("=" * 60)

    # 纯文本场景（传统 Pipeline）
    plain_text_output = """
    定积分的知识点有牛顿莱布尼茨公式、定积分概念、定积分应用。
    建议先学极限和导数，再学定积分。学生容易搞混不定积分和定积分。
    """

    # 结构化场景（PentAGI 式）
    structured_output = AgentMessage(
        agent_name="knowledge_mapper",
        task="拆解定积分知识点",
        status=AgentStatus.SUCCESS,
        artifact="## 知识树\n- 定积分概念 (★☆☆)\n- 牛顿-莱布尼茨公式 (★★☆)\n- 定积分应用 (★★★)",
        summary="定积分拆解为3个层级，覆盖概念→公式→应用",
        confidence=0.85,
        metadata={"knowledge_count": 3, "has_dependencies": True, "has_warnings": True},
    )

    print(f"\n📊 纯文本模式:")
    print(f"   下游 Agent 只能收到: {plain_text_output[:80]}...")
    print(f"   问题: 无法判断质量、状态不明、无置信度")

    print(f"\n📊 结构化协议模式:")
    print(f"   下游 Agent 收到 AgentMessage:")
    print(f"   - 状态: {structured_output.status}")
    print(f"   - 置信度: {structured_output.confidence:.0%}")
    print(f"   - 摘要: {structured_output.summary}")
    print(f"   - 元数据: {structured_output.metadata}")
    print(f"   优势: 可直接判断质量、决定是否重试、提取摘要")

    print(f"\n💡 结论: 结构化协议让下游 Agent 能基于置信度做决策，而不是盲猜上次输出质量。")

    # 保存对比报告
    comparison = f"""# Pipeline 通信协议对比

## 纯文本模式
```
{plain_text_output}
```
**问题**: 无状态标记、无置信度、无摘要，下游 Agent 盲猜质量。

## 结构化协议（PentAGI 式）
```json
{structured_output.to_json()}
```
**优势**: 状态显式、置信度可量化、摘要即取即用、元数据指导重试。
"""
    comparison_path = Path(__file__).resolve().parent.parent / "protocol_comparison.md"
    comparison_path.write_text(comparison, encoding="utf-8")
    print(f"  📄 对比文档已保存: {comparison_path}")


if __name__ == "__main__":
    print("🚀 EduAgent Pipeline 实验 — PentAGI 式结构化通信")
    print()

    experiment_1_structured_protocol()
    experiment_2_reporter_agent()
    experiment_3_comparison()

    print("\n" + "=" * 60)
    print("✅ 三个实验全部完成！")
    print("=" * 60)
    print("""
📊 产出文件:
  1. pipeline_report_demo.md      — 结构化报告示例
  2. pipeline_report_newton.md    — 牛顿力学完整报告
  3. protocol_comparison.md       — 协议对比文档

💡 关键收获:
  - 结构化 JSON 通信 > 纯文本传递
  - AgentMessage 让下游 Agent 能基于置信度决策
  - ReporterAgent 让 Pipeline 输出自动变成可交付报告
  - 这套模式直接可移植到 Francis 的协作实验
""")
