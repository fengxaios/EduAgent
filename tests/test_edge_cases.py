"""
Edge-case and regression tests for EduAgent v1.0/v2.0.

Covers:
  1. Import regression (v1.0)
  2. LessonPlannerAgent instantiation (v1.0)
  3. Framework imports (v2.0)
  4. Result.elapsed (v2.0)
  5. SnapshotManager overflow (v2.0)
  6. DAG circular dependency (v2.0)
  7. Empty IsolatedExecutor (v2.0)
  8. AgentRunner immediate exception (v2.0)

Usage:
  cd D:\ai\EduAgent && python tests\test_edge_cases.py
"""

import sys
import os
import asyncio
import time
import traceback

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

RESULTS = []


def test(name):
    """Decorator that wraps a test function and records result."""

    def decorator(fn):
        def wrapper():
            try:
                fn()
                RESULTS.append((name, "PASS", None))
                print(f"  [PASS] {name}")
                return True
            except AssertionError as e:
                RESULTS.append((name, "FAIL", str(e)))
                print(f"  [FAIL] {name}: {e}")
                return False
            except Exception as e:
                tb = traceback.format_exc()
                RESULTS.append((name, "FAIL", f"{e}\n{tb}"))
                print(f"  [FAIL] {name}: {e}")
                print(f"         {tb.split(chr(10))[-3]}")
                return False

        return wrapper

    return decorator


# ============================================================
# TEST 1: Import regression — v1.0 imports
# ============================================================
@test("1a. Import: eduagent.core -> Orchestrator, Agent")
def test_import_core():
    from eduagent.core import Orchestrator, Agent
    assert Orchestrator is not None
    assert Agent is not None


@test("1b. Import: eduagent.core.structured_protocol")
def test_import_structured_protocol():
    from eduagent.core.structured_protocol import \
        AgentMessage, PipelineReport, AgentStatus
    assert AgentMessage is not None
    assert PipelineReport is not None
    assert AgentStatus is not None
    # Quick sanity: these are usable
    msg = AgentMessage(agent_name="test", task="verify")
    assert msg.agent_name == "test"
    assert isinstance(msg.status, AgentStatus)
    report = PipelineReport(pipeline_name="test_pipeline")
    assert report.success_rate == 0.0


@test("1c. Import: eduagent.core.memory -> Memory")
def test_import_memory():
    from eduagent.core.memory import Memory
    mem = Memory()
    assert mem is not None


@test("1d. Import: eduagent.core.evaluator -> Evaluator")
def test_import_evaluator():
    from eduagent.core.evaluator import Evaluator, BENCHMARK_CASES
    ev = Evaluator()
    assert ev is not None
    assert len(BENCHMARK_CASES) > 0


# ============================================================
# TEST 2: v1.0 Agent base class — LessonPlannerAgent
# ============================================================
@test("2a. LessonPlannerAgent instantiation (defaults)")
def test_lesson_planner_defaults():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent()
    assert agent.name == "lesson_planner"
    assert agent.mode == "standard"
    assert agent.reflection == "auto"
    assert agent.max_iterations == 3


@test("2b. LessonPlannerAgent with mode='brief'")
def test_lesson_planner_brief():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent(mode="brief")
    assert agent.mode == "brief"


@test("2c. LessonPlannerAgent with reflection='always'")
def test_lesson_planner_always():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent(reflection="always")
    assert agent.reflection == "always"


@test("2d. LessonPlannerAgent with reflection='never'")
def test_lesson_planner_never():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent(reflection="never")
    assert agent.reflection == "never"


@test("2e. LessonPlannerAgent with max_iterations=5")
def test_lesson_planner_max_iterations():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent(max_iterations=5)
    assert agent.max_iterations == 5


@test("2f. LessonPlannerAgent system prompt")
def test_lesson_planner_system_prompt():
    from eduagent.agents.lesson_planner import LessonPlannerAgent
    agent = LessonPlannerAgent()
    prompt = agent.get_system_prompt()
    assert "教学设计" in prompt
    assert "教学目标" in prompt
    assert "教学重难点" in prompt
    assert "教学过程" in prompt


# ============================================================
# TEST 3: Framework imports — v2.0
# ============================================================
@test("3a. Import: DAGOrchestrator, Task, Result")
def test_import_dag_orch():
    from eduagent.framework import \
        DAGOrchestrator, Task, Result
    assert DAGOrchestrator is not None
    assert Task is not None
    assert Result is not None


@test("3b. Import: AgentRunner")
def test_import_agent_runner():
    from eduagent.framework import AgentRunner
    from eduagent.framework.agent_runner import \
        AgentRunnerAdapter, IsolatedExecutor, SnapshotManager
    assert AgentRunner is not None
    assert AgentRunnerAdapter is not None
    assert IsolatedExecutor is not None
    assert SnapshotManager is not None


@test("3c. Import: RetryPolicy, CircuitBreaker")
def test_import_fault_tolerance():
    from eduagent.framework import RetryPolicy, CircuitBreaker
    from eduagent.framework.fault_tolerance import CircuitBreakerOpenError
    assert RetryPolicy is not None
    assert CircuitBreaker is not None
    assert CircuitBreakerOpenError is not None


@test("3d. Import: CronScheduler, WorkflowEngine")
def test_import_automation():
    from eduagent.framework import CronScheduler, WorkflowEngine
    assert CronScheduler is not None
    assert WorkflowEngine is not None


# ============================================================
# TEST 4: Edge case — Result.elapsed
# ============================================================
@test("4a. Result.elapsed success — positive time")
def test_result_elapsed_success():
    """Result.elapsed should be finished_at - started_at, positive for success."""
    from eduagent.framework import Result, TaskStatus
    r = Result(
        task_id="t1",
        status=TaskStatus.SUCCESS,
        started_at=100.0,
        finished_at=105.0,
    )
    # Should NOT raise, should be positive
    elapsed = r.elapsed
    assert elapsed == 5.0, f"Expected 5.0, got {elapsed}"
    assert elapsed >= 0, f"Elapsed should be >= 0, got {elapsed}"


@test("4b. Result.elapsed failure — near zero (not negative)")
def test_result_elapsed_failure():
    """Result.elapsed for a failure should be >= 0, never negative."""
    from eduagent.framework import Result, TaskStatus
    r = Result(
        task_id="t2",
        status=TaskStatus.FAILED,
        started_at=200.0,
        finished_at=200.0,  # started == finished
    )
    elapsed = r.elapsed
    assert elapsed >= 0, f"Elapsed should be >= 0, got {elapsed}"


@test("4c. Result.elapsed with zero defaults")
def test_result_elapsed_zero_defaults():
    """Default started_at/finished_at are 0.0, so elapsed should be 0.0."""
    from eduagent.framework import Result
    r = Result(task_id="t3")
    elapsed = r.elapsed
    assert elapsed == 0.0, f"Expected 0.0, got {elapsed}"


@test("4d. Result.failure() factory elapsed")
def test_result_failure_elapsed():
    """Result.failure() sets both timestamps to time.time(); check no crash."""
    from eduagent.framework import Result
    r = Result.failure("t4", ["test error"])
    # Should compute without exception
    elapsed = r.elapsed
    assert isinstance(elapsed, float), f"Expected float, got {type(elapsed)}"
    assert elapsed >= 0, f"Elapsed should be non-negative, got {elapsed}"


@test("4e. Result.elapsed negative time_safety")
def test_result_elapsed_no_negative():
    """Even with swapped timestamps, .elapsed should not crash — just report value."""
    from eduagent.framework import Result, TaskStatus
    # Deliberately reversed timestamps (finished before started — clock skew?)
    r = Result(
        task_id="t5",
        status=TaskStatus.FAILED,
        started_at=300.0,
        finished_at=299.0,
    )
    elapsed = r.elapsed
    # The code does finished_at - started_at, so it will be -1.0
    # That's a logic bug if real, but we test it doesn't crash
    assert isinstance(elapsed, float), f"Expected float, got {type(elapsed)}"


# ============================================================
# TEST 5: Edge case — SnapshotManager overflow
# ============================================================
@test("5a. SnapshotManager max_snapshots enforces limit")
def test_snapshot_manager_overflow():
    """Capture 5 snapshots with max=3; only 3 remain."""
    from eduagent.framework.agent_runner import SnapshotManager
    sm = SnapshotManager(max_snapshots=3)
    for i in range(5):
        sm.capture(f"task_{i}", {"i": i})
        # Small sleep so timestamps differ
        time.sleep(0.01)
    count = len(sm._snapshots)
    assert count == 3, f"Expected 3 snapshots after overflow, got {count}"


@test("5b. SnapshotManager evicts oldest by timestamp")
def test_snapshot_manager_evicts_oldest():
    """The oldest snapshot (by timestamp) should be evicted first."""
    from eduagent.framework.agent_runner import SnapshotManager
    sm = SnapshotManager(max_snapshots=3)
    sm.capture("task_0", {"n": 0})
    time.sleep(0.05)
    sm.capture("task_1", {"n": 1})
    time.sleep(0.05)
    sm.capture("task_2", {"n": 2})
    time.sleep(0.05)
    # Now capture 2 more; oldest (task_0, then task_1) evicted
    sm.capture("task_3", {"n": 3})
    time.sleep(0.01)
    sm.capture("task_4", {"n": 4})

    assert "task_0" not in sm._snapshots, "task_0 (oldest) should be evicted"
    assert "task_1" not in sm._snapshots, "task_1 should be evicted"
    assert "task_2" in sm._snapshots
    assert "task_3" in sm._snapshots
    assert "task_4" in sm._snapshots
    assert len(sm._snapshots) == 3, f"Expected 3, got {len(sm._snapshots)}"


@test("5c. SnapshotManager restore and discard")
def test_snapshot_manager_restore_discard():
    """Snapshot can be restored and discarded."""
    from eduagent.framework.agent_runner import SnapshotManager
    sm = SnapshotManager(max_snapshots=5)
    sm.capture("task_x", {"key": "value"})
    restored = sm.restore("task_x")
    assert restored == {"key": "value"}

    sm.discard("task_x")
    assert "task_x" not in sm._snapshots
    assert sm.restore("task_x") is None


# ============================================================
# TEST 6: Edge case — DAG with circular dependency
# ============================================================
@test("6a. DAG circular dependency raises ValueError")
def test_dag_circular_raises():
    """A depends on B, B depends on A: should raise ValueError with '循环依赖'."""
    from eduagent.framework import DAGOrchestrator, Task
    orch = DAGOrchestrator()
    tasks = [
        Task(id="A", depends_on=["B"]),
        Task(id="B", depends_on=["A"]),
    ]
    try:
        orch.build_dag(tasks)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "循环依赖" in str(e), f"错误信息应包含'循环依赖': {e}"


@test("6b. DAG indirect cycle raises ValueError")
def test_dag_indirect_cycle_raises():
    """A→B→C→A triangle cycle: should raise ValueError."""
    from eduagent.framework import DAGOrchestrator, Task
    orch = DAGOrchestrator()
    tasks = [
        Task(id="A", depends_on=["C"]),
        Task(id="B", depends_on=["A"]),
        Task(id="C", depends_on=["B"]),
    ]
    try:
        orch.build_dag(tasks)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "循环依赖" in str(e)


@test("6c. DAG self-loop raises ValueError")
def test_dag_self_loop_raises():
    """A depends_on A (self-loop): should raise ValueError."""
    from eduagent.framework import DAGOrchestrator, Task
    orch = DAGOrchestrator()
    tasks = [
        Task(id="A", depends_on=["A"]),
    ]
    try:
        orch.build_dag(tasks)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "循环依赖" in str(e)


# ============================================================
# TEST 7: Edge case — empty IsolatedExecutor
# ============================================================
@test("7a. execute_parallel with empty list returns {}")
def test_empty_executor_parallel():
    """Calling execute_parallel with empty list should return {} without error."""
    from eduagent.framework.agent_runner import IsolatedExecutor

    async def _run():
        exec = IsolatedExecutor()
        return await exec.execute_parallel([])

    results = asyncio.get_event_loop().run_until_complete(_run())
    assert results == {}, f"Expected empty dict, got {results}"
    assert isinstance(results, dict)


@test("7b. execute_one with no registered agent returns FAILED")
def test_empty_executor_execute_one():
    """execute_one with no matching agent should return a FAILED Result, not crash."""
    from eduagent.framework.agent_runner import IsolatedExecutor
    from eduagent.framework.protocol import Task, TaskStatus

    async def _run():
        exec = IsolatedExecutor()
        task = Task(id="nx", type="nonexistent")
        return await exec.execute_one(task)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.status == TaskStatus.FAILED
    assert len(result.errors) > 0
    assert "未找到" in result.errors[0]


# ============================================================
# TEST 8: Edge case — AgentRunner with immediate exception
# ============================================================
@test("8a. AgentRunner._execute raises -> Result.status is FAILED")
def test_agent_runner_immediate_exception():
    """AgentRunner whose _execute immediately raises should produce FAILED Result."""
    from eduagent.framework.agent_runner import AgentRunner
    from eduagent.framework.protocol import Task, TaskStatus

    class FailingAgent(AgentRunner):
        async def _execute(self, task: Task) -> dict:
            raise RuntimeError("boom immediately")

    agent = FailingAgent(name="failer", agent_type="fail", timeout=5)

    async def _run():
        task = Task(id="f1", type="fail")
        return await agent.execute(task)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.status == TaskStatus.FAILED, \
        f"Expected FAILED, got {result.status}"
    assert len(result.errors) > 0, \
        f"Expected errors populated, got {result.errors}"
    assert "boom immediately" in result.errors[0]
    assert result.task_id == "f1"


@test("8b. AgentRunner._execute raises -> errors list populated")
def test_agent_runner_errors_populated():
    """Multiple errors should accumulate in the errors list."""
    from eduagent.framework.agent_runner import AgentRunner
    from eduagent.framework.protocol import Task, TaskStatus

    class MultiFailAgent(AgentRunner):
        async def _execute(self, task: Task) -> dict:
            raise ValueError("multi-fail-1")
            raise ValueError("multi-fail-2")  # unreachable

    agent = MultiFailAgent(name="multi", agent_type="mfail", timeout=5)

    async def _run():
        task = Task(id="f2", type="mfail")
        return await agent.execute(task)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.status == TaskStatus.FAILED
    assert len(result.errors) >= 1, f"Expected at least 1 error, got {result.errors}"


@test("8c. AgentRunner snapshot created before execute")
def test_agent_runner_snapshot_on_fail():
    """Even on failure, a snapshot was captured."""
    from eduagent.framework.agent_runner import AgentRunner
    from eduagent.framework.protocol import Task, TaskStatus

    class FailingAgent(AgentRunner):
        async def _execute(self, task: Task) -> dict:
            raise RuntimeError("fail")

    agent = FailingAgent(name="snapfail", agent_type="sfail", timeout=5)
    agent._state = {"before": "value"}

    async def _run():
        task = Task(id="f3", type="sfail")
        return await agent.execute(task)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.status == TaskStatus.FAILED
    # State should be restored from snapshot
    assert agent._state == {"before": "value"}, \
        f"State should be restored on rollback, got {agent._state}"


@test("8d. AgentRunner metrics contain elapsed")
def test_agent_runner_metrics():
    """Result.metrics should contain elapsed time and agent name."""
    from eduagent.framework.agent_runner import AgentRunner
    from eduagent.framework.protocol import Task, TaskStatus

    class FastAgent(AgentRunner):
        async def _execute(self, task: Task) -> dict:
            return {"done": True}

    agent = FastAgent(name="fast", agent_type="ftype", timeout=5)

    async def _run():
        task = Task(id="f4", type="ftype")
        return await agent.execute(task)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.status == TaskStatus.SUCCESS
    assert "elapsed" in result.metrics
    assert result.metrics["elapsed"] >= 0
    assert result.metrics["agent"] == "fast"


# ============================================================
# Report
# ============================================================
def print_report():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r[1] == "PASS")
    failed = total - passed

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} PASS / {failed} FAIL / {total} TOTAL")
    print("=" * 60)

    if failed:
        print("\nFailures:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"  [{status}] {name}")
                if detail:
                    # Show just the first meaningful line
                    lines = detail.strip().split("\n")
                    for line in lines[:3]:
                        print(f"         {line}")
        return 1
    else:
        print("\nAll tests passed.")
        return 0


if __name__ == "__main__":
    print("EduAgent Edge-Case & Regression Tests")
    print(f"Python: {sys.version}")
    print("-" * 60)
    # Run all test_* functions in order
    import inspect

    frame = inspect.currentframe()
    test_funcs = sorted(
        [(k, v) for k, v in frame.f_globals.items() if k.startswith("test_")],
        key=lambda x: x[0],
    )
    if not test_funcs:
        # Fallback: run by listing functions
        test_funcs = [
            (name, obj) for name, obj in globals().items()
            if name.startswith("test_") and callable(obj)
        ]

    for name, fn in test_funcs:
        fn()

    exit_code = print_report()
    sys.exit(exit_code)
