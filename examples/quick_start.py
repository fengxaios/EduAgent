"""
EduAgent 使用示例 —— 三分钟上手
"""

from core import Orchestrator
from agents import LessonPlannerAgent, QuizGeneratorAgent, KnowledgeMapperAgent


# 1. 初始化编排器（从环境变量读取 API Key）
orchestrator = Orchestrator()  # 读取 DASHSCOPE_API_KEY 环境变量

# 2. 注册所有教学 Agent
orchestrator.register_all([
    LessonPlannerAgent(),
    QuizGeneratorAgent(),
    KnowledgeMapperAgent(),
])

print("EduAgent 就绪 ✅")
print(f"已注册 Agent: {orchestrator.get_status()['registered_agents']}")

# 3. 执行任务 — 自动路由到合适的 Agent

# 示例1：教案生成
result = orchestrator.route("为高中二年级设计一节「导数与切线」的教案")
print(f"\n📐 [{result['agent']}]")
print(result['result'][:300] + "...")

# 示例2：习题生成
result = orchestrator.route("出5道关于极限运算的高数基础题，含答案和解析")
print(f"\n📝 [{result['agent']}]")
print(result['result'][:300] + "...")

# 示例3：知识点拆解
result = orchestrator.route("拆解「微分中值定理」章节的知识点体系")
print(f"\n🧮 [{result['agent']}]")
print(result['result'][:300] + "...")

# 4. 管线协作：先拆解知识点 → 生成教案 → 配套习题
print("\n🚀 管线协作示例:")
results = orchestrator.pipeline([
    {"agent": "knowledge_mapper", "task": "拆解「定积分」知识点"},
    {"agent": "lesson_planner", "task": "基于知识点拆解结果，生成一节定积分教案"},
    {"agent": "quiz_generator", "task": "为以上教案出5道配套练习题"},
])
for r in results:
    if "error" in r:
        print(f"  ❌ {r['agent']}: {r['error']}")
    else:
        print(f"  ✅ {r['agent']}: {r['result'][:100]}...")
