"""
EduAgent v2.0 集成演示

展示 framework 模块如何与现有 core 模块协同工作。

运行: python examples/framework_demo.py
"""

import asyncio
import sys
import io
import os

# Fix Windows GBK encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from eduagent.framework import (
    DAGOrchestrator, Task, Result, AcceptanceCriteria,
    AgentRunner, AgentRunnerAdapter,
    RetryPolicy, CircuitBreaker,
    CronScheduler, WorkflowEngine, WorkflowStep,
)


# ═══════════════════════════════════════════════════
# 定义 v2.0 Agent（继承 AgentRunner）
# ═══════════════════════════════════════════════════

class PPTAgent(AgentRunner):
    """课件PPT生成Agent"""

    def __init__(self):
        super().__init__(name="PPT-Generator", agent_type="ppt", timeout=120)

    async def _execute(self, task: Task) -> dict:
        topic = task.payload.get("topic", "未知主题")
        await asyncio.sleep(1)  # simulate work
        return {
            "slides": 15,
            "outline": [f"{topic} - 第{i}页" for i in range(1, 16)],
            "file_path": f"/output/{task.id}_课件.pptx",
        }


class KnowledgeAgent(AgentRunner):
    """知识点拆解Agent"""

    def __init__(self):
        super().__init__(name="Knowledge-Breakdown", agent_type="knowledge", timeout=60)

    async def _execute(self, task: Task) -> dict:
        topic = task.payload.get("topic", "未知主题")
        await asyncio.sleep(0.5)
        return {
            "concepts": [
                {"name": f"{topic}-概念{i}", "difficulty": "★★★☆☆", "time": "15min"}
                for i in range(1, 6)
            ],
            "prerequisites": ["前置知识A", "前置知识B"],
        }


class ExerciseAgent(AgentRunner):
    """习题生成Agent — 依赖上游知识点"""

    def __init__(self):
        super().__init__(name="Exercise-Generator", agent_type="exercise", timeout=60)

    async def _execute(self, task: Task) -> dict:
        # 从上游知识点获取 context
        knowledge_data = task.context.get("knowledge", {})
        concepts = knowledge_data.get("concepts", [])
        await asyncio.sleep(1.5)
        return {
            "exercises": [
                {"type": "选择题", "stem": f"关于{concept['name']}的说法正确的是？",
                 "options": ["A", "B", "C", "D"], "answer": "B"}
                for concept in concepts
            ],
            "total": len(concepts),
        }


class StoryboardAgent(AgentRunner):
    """分镜脚本Agent — 独立无依赖"""

    def __init__(self):
        super().__init__(name="Storyboard-Generator", agent_type="storyboard", timeout=90)

    async def _execute(self, task: Task) -> dict:
        topic = task.payload.get("topic", "未知主题")
        await asyncio.sleep(2)
        return {
            "scenes": [
                {"no": i, "duration": "15s", "description": f"{topic}场景{i}"}
                for i in range(1, 6)
            ],
            "total_duration": "75s",
        }


# ═══════════════════════════════════════════════════
# 演示 1: DAG 并行调度
# ═══════════════════════════════════════════════════

async def demo_dag_parallel():
    print("\n" + "=" * 60)
    print("  演示 1: DAG 分层并行执行")
    print("=" * 60)

    orch = DAGOrchestrator()
    orch.register(PPTAgent())
    orch.register(KnowledgeAgent())
    orch.register(ExerciseAgent())
    orch.register(StoryboardAgent())

    #   DAG 依赖关系:
    #     ppt ────────────────┐
    #     knowledge ──────────┤── Level 0 (3个并行)
    #     storyboard ────────┘
    #        │
    #     exercise ────────────── Level 1 (依赖 knowledge)

    tasks = [
        Task(id="ppt",          type="ppt",        payload={"topic": "微积分入门"}, depends_on=[]),
        Task(id="knowledge",    type="knowledge",  payload={"topic": "微积分入门"}, depends_on=[]),
        Task(id="exercise",     type="exercise",   payload={"topic": "微积分入门"}, depends_on=["knowledge"]),
        Task(id="storyboard",   type="storyboard", payload={"topic": "微积分入门"}, depends_on=[]),
    ]

    import time
    start = time.time()
    results = await orch.run_dag(tasks)
    elapsed = time.time() - start

    print(f"\n📊 执行结果 ({elapsed:.1f}s):")
    for tid, r in results.items():
        icon = "✅" if r.ok else "❌"
        print(f"  {icon} [{tid}] {r.status.value} | {r.metrics.get('elapsed', 0):.1f}s")
        if r.ok:
            for k in r.data:
                val = str(r.data[k])
                print(f"        {k}: {val[:60]}{'...' if len(val) > 60 else ''}")

    print(f"\n⏱ 总耗时: {elapsed:.1f}s (串行需约 5.0s)")
    return results


# ═══════════════════════════════════════════════════
# 演示 2: 容错系统
# ═══════════════════════════════════════════════════

async def demo_fault_tolerance():
    print("\n" + "=" * 60)
    print("  演示 2: 容错系统 — 重试 + 熔断")
    print("=" * 60)

    # ── 重试策略 ──
    policy = RetryPolicy(max_retries=3, base_delay=0.1)

    call_count = [0]

    async def flaky_api():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError(f"模拟网络错误 (第{call_count[0]}次)")
        return {"data": "终于成功了!"}

    try:
        result = await policy.execute(flaky_api, task_id="demo-task")
        print(f"  ✅ 重试成功 (共调用{call_count[0]}次): {result}")
    except Exception as e:
        print(f"  ❌ 重试失败: {e}")

    # ── 熔断器 ──
    breaker = CircuitBreaker(name="demo", failure_threshold=3, recovery_timeout=5)

    @breaker.protect
    async def unstable_service(should_fail: bool):
        if should_fail:
            raise RuntimeError("服务异常")
        return "OK"

    # 连续失败触发熔断
    for i in range(5):
        try:
            await unstable_service(True)
        except (RuntimeError, Exception) as e:
            pass
    print(f"  🔌 熔断器状态: {breaker.state.value} (连续失败5次后)")
    print(f"     熔断器是否开着: {breaker.is_open}")


# ═══════════════════════════════════════════════════
# 演示 3: 自动化系统
# ═══════════════════════════════════════════════════

async def demo_automation():
    print("\n" + "=" * 60)
    print("  演示 3: 自动化 — Cron + Workflow")
    print("=" * 60)

    # ── Cron 调度器 ──
    scheduler = CronScheduler()

    async def heartbeat():
        return {"status": "ok", "agents": 4}

    async def daily_review():
        return {"memories_consolidated": 12}

    scheduler.add("heartbeat", "30m", heartbeat, timeout=10)
    scheduler.add("daily_review", "0 21 * * *", daily_review, timeout=120)
    print(f"  📅 已注册 {len(scheduler._jobs)} 个定时任务")

    # ── 工作流引擎 ──
    wf = WorkflowEngine()

    async def fetch(ctx):
        print("  📥 获取素材...")
        return {"images": 5}

    async def design(ctx):
        print("  🎨 设计PPT...")
        materials = ctx.get("fetch", {})
        return {"slides": 10, "images_used": materials.get("images", 0)}

    async def script(ctx):
        print("  ✍️ 生成讲稿...")
        ppt = ctx.get("design", {})
        return {"pages": ppt.get("slides", 0), "words": 2000}

    wf.add_step(WorkflowStep("fetch", fetch))
    wf.add_step(WorkflowStep("design", design, depends_on=["fetch"]))
    wf.add_step(WorkflowStep("script", script, depends_on=["design"]))

    results = await wf.run()
    print(f"  ✅ 工作流完成: {list(results.keys())}")


# ═══════════════════════════════════════════════════
# 演示 4: v1.0 → v2.0 适配
# ═══════════════════════════════════════════════════

async def demo_v1_adapter():
    print("\n" + "=" * 60)
    print("  演示 4: v1.0 Agent → v2.0 AgentRunner 适配")
    print("=" * 60)

    # 模拟一个 v1.0 Agent
    class MockV1Agent:
        def __init__(self):
            self.name = "MockAgent"

        def run(self, task, **context):
            return {"output": f"处理了: {task}", "context_keys": list(context.keys())}

    v1 = MockV1Agent()
    runner = AgentRunnerAdapter.wrap(v1, agent_type="mock", timeout=10)

    task = Task(type="mock", payload={"prompt": "测试任务"})
    result = await runner.execute(task)

    print(f"  {'✅' if result.ok else '❌'} 适配成功: {result.data.get('output', 'N/A')}")

    return result


# ═══════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("  EduAgent v2.0 Framework — 全部演示")
    print("=" * 60)

    await demo_dag_parallel()
    await demo_fault_tolerance()
    await demo_automation()
    await demo_v1_adapter()

    print("\n" + "=" * 60)
    print("  ✅ 全部演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
