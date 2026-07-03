"""
EduAgent 使用示例 —— 三分钟上手

安装: pip install -e .
"""

from eduagent import Orchestrator, LessonPlannerAgent, QuizGeneratorAgent, KnowledgeMapperAgent


# 1. 初始化编排器（从 .env 或环境变量读取 API Key）
orchestrator = Orchestrator()

# 2. 注册教学 Agent
orchestrator.register_all([
    LessonPlannerAgent(),
    QuizGeneratorAgent(),
    KnowledgeMapperAgent(),
])

print(f"EduAgent 就绪 | 已注册: {orchestrator.get_status()['registered_agents']}")

# 3. 智能路由：自动分配合适的 Agent
result = orchestrator.route("为高中二年级设计一节导数与切线的教案（brief模式）")
print(f"\n[{result['agent']}] {result['result'][:300]}...")

# 4. 管线协作：多 Agent 串行
results = orchestrator.pipeline([
    {"agent": "knowledge_mapper", "task": "拆解定积分知识点"},
    {"agent": "lesson_planner", "task": "基于拆解结果生成一节定积分教案"},
    {"agent": "quiz_generator", "task": "出5道配套练习题"},
])
for r in results:
    status = "ERROR" if "error" in r else "OK"
    print(f"  [{status}] {r['agent']}: {r.get('result', r.get('error', ''))[:80]}...")
