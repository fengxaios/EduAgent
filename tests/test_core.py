"""
核心模块单元测试 —— 包含 LLM Mock，覆盖核心路径

运行: pytest tests/ -v
"""

import json
import tempfile
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from eduagent.core import Agent, Memory, ToolRegistry, tool, Evaluator
from eduagent.core.agent import MODE_INSTRUCTIONS


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def memory():
    return Memory(max_conversation_turns=10)


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def mock_client():
    """创建一个 Mock OpenAI client"""
    client = MagicMock()
    return client


@pytest.fixture
def simple_agent(mock_client):
    """创建一个带 Mock client 的基础 Agent"""

    class TestAgent(Agent):
        def get_system_prompt(self) -> str:
            return "你是一个测试助手"

    agent = TestAgent(name="test_agent")
    agent.configure_llm(mock_client)
    return agent


# ═══════════════════════════════════════════
# Memory Tests
# ═══════════════════════════════════════════

class TestMemory:
    def test_add_and_get_context(self, memory):
        memory.add_message("user", "你好")
        memory.add_message("assistant", "你好！")
        ctx = memory.get_context(last_n=1)
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"

    def test_knowledge_store(self, memory):
        memory.set_knowledge("math.topic", "微积分")
        assert memory.get_knowledge("math.topic") == "微积分"
        assert memory.get_knowledge("nonexistent", "default") == "default"

    def test_knowledge_search(self, memory):
        memory.set_knowledge("python.version", "3.10")
        memory.set_knowledge("project.name", "EduAgent")
        results = memory.search_knowledge("python")
        assert len(results) == 1
        results_empty = memory.search_knowledge("java")
        assert len(results_empty) == 0

    def test_trim(self, memory):
        memory.max_turns = 2
        for i in range(5):
            memory.add_message("user", f"msg{i}")
            memory.add_message("assistant", f"reply{i}")
        ctx = memory.get_context(last_n=10)
        # 保留最近 2 轮 = 4 条消息
        assert len(ctx) <= 5

    def test_clear_conversation(self, memory):
        memory.add_message("user", "hello")
        memory.add_message("assistant", "hi")
        assert len(memory.get_context(10)) == 2
        memory.clear_conversation()
        assert len(memory.get_context(10)) == 0

    def test_summary(self, memory):
        memory.add_message("user", "a")
        memory.add_message("assistant", "b")
        memory.set_knowledge("k1", "v1")
        summary = memory.summary()
        assert summary["conversation_turns"] == 1
        assert summary["knowledge_items"] == 1

    def test_persistence_roundtrip(self, memory):
        """测试持久化 → 加载的完整周期"""
        memory.add_message("user", "测试消息")
        memory.add_message("assistant", "回复消息")
        memory.set_knowledge("key1", "value1")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name

        try:
            memory.save(tmp_path)
            loaded = Memory.load(tmp_path)
            assert loaded.summary() == memory.summary()
            ctx = loaded.get_context(last_n=1)
            assert ctx[0]["content"] == "测试消息"
            assert loaded.get_knowledge("key1") == "value1"
        finally:
            os.unlink(tmp_path)


# ═══════════════════════════════════════════
# ToolRegistry Tests
# ═══════════════════════════════════════════

class TestToolRegistry:
    def test_register_and_call(self, registry):
        @registry.register(description="加法运算")
        def add(a: int, b: int) -> int:
            return a + b

        result = registry.call("add", a=1, b=2)
        assert result == 3

    def test_get_schema(self, registry):
        @registry.register(description="问候")
        def greet(name: str) -> str:
            return f"Hello, {name}"

        schema = registry.get_schema()
        assert len(schema) == 1
        assert schema[0]["type"] == "function"
        assert schema[0]["function"]["name"] == "greet"
        assert "name" in schema[0]["function"]["parameters"]["properties"]

    def test_call_unregistered_raises(self, registry):
        with pytest.raises(ValueError, match="未注册"):
            registry.call("nonexistent")

    def test_register_duplicate_overwrites(self, registry):
        @registry.register(name="test", description="first")
        def func1():
            return 1

        @registry.register(name="test", description="second")
        def func2():
            return 2

        assert registry.call("test") == 2

    def test_empty_schema(self, registry):
        assert registry.get_schema() == []


# ═══════════════════════════════════════════
# Agent Base Tests (with LLM Mock)
# ═══════════════════════════════════════════

class TestAgentBase:
    def test_agent_creation(self):
        class TestAgent(Agent):
            def get_system_prompt(self) -> str:
                return "你是一个测试助手"

        agent = TestAgent(name="test")
        assert agent.name == "test"
        assert agent.mode == "standard"
        assert agent.max_iterations == 3

    def test_configure_llm(self, simple_agent, mock_client):
        assert simple_agent.client is mock_client

    def test_call_llm_no_client_raises(self):
        class TestAgent(Agent):
            def get_system_prompt(self) -> str:
                return "test"

        agent = TestAgent(name="test")
        with pytest.raises(RuntimeError, match="LLM 客户端未配置"):
            agent._call_llm("hello")

    def test_clean_output_strips_code_block(self, simple_agent):
        text = "```markdown\n# 标题\n内容\n```"
        cleaned = simple_agent._clean_output(text)
        assert cleaned == "# 标题\n内容"

    def test_clean_output_no_code_block(self, simple_agent):
        text = "# 普通标题\n内容"
        cleaned = simple_agent._clean_output(text)
        assert cleaned == text.strip()

    def test_should_reflect_brief_mode(self, simple_agent):
        simple_agent.mode = "brief"
        assert simple_agent._should_reflect("anything") is False

    def test_should_reflect_always(self, simple_agent):
        simple_agent.reflection = "always"
        assert simple_agent._should_reflect("anything") is True

    def test_should_reflect_never(self, simple_agent):
        simple_agent.reflection = "never"
        assert simple_agent._should_reflect("anything") is False

    def test_should_reflect_auto_short(self, simple_agent):
        simple_agent.reflection = "auto"
        simple_agent.mode = "detailed"
        assert simple_agent._should_reflect("too short") is True

    def test_should_reflect_auto_no_structure(self, simple_agent):
        simple_agent.reflection = "auto"
        simple_agent.mode = "detailed"
        output = "没有标题结构的纯文本输出 " * 15
        assert simple_agent._should_reflect(output) is True

    def test_should_reflect_auto_good_output(self, simple_agent):
        simple_agent.reflection = "auto"
        simple_agent.mode = "detailed"
        output = "# 标题\n\n## 第一节\n内容" + "x" * 300
        assert simple_agent._should_reflect(output) is False

    def test_load_template(self, simple_agent):
        """验证模板加载功能"""
        tmpl = simple_agent.load_template("lesson_plan_template")
        assert "基本信息" in tmpl
        assert "教学目标" in tmpl

    def test_load_template_nonexistent(self, simple_agent):
        with pytest.raises(FileNotFoundError):
            simple_agent.load_template("nonexistent_template")

    # ── LLM Mock 测试 ──

    def test_call_llm_basic(self, simple_agent, mock_client):
        """测试基本 LLM 调用"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="这是回复内容"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = simple_agent._call_llm("你好", system="系统提示")

        assert result == "这是回复内容"
        # 验证调用参数
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "qwen-plus"

    def test_call_llm_with_tools_no_tool_calls(self, simple_agent, mock_client):
        """测试工具调用场景——LLM 不调用工具直接返回"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content="直接回答，无需工具",
                tool_calls=None,
            ))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = simple_agent._call_llm_with_tools("系统", "任务")

        assert result == "直接回答，无需工具"

    def test_call_llm_with_tools_single_round(self, simple_agent, mock_client, registry):
        """测试单轮工具调用"""
        @registry.register(description="获取天气")
        def get_weather(city: str) -> str:
            return f"{city}: 晴天 25°C"

        simple_agent.tools = registry

        # 第一轮返回 tool_calls
        resp1 = MagicMock()
        tool_call = MagicMock()
        tool_call.id = "call_001"
        tool_call.function.name = "get_weather"
        tool_call.function.arguments = '{"city": "北京"}'
        resp1.choices = [MagicMock(message=MagicMock(
            content=None,
            tool_calls=[tool_call],
        ))]

        # 第二轮返回最终文本
        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=MagicMock(
            content="北京今天晴天，25°C，适合出行。",
        ))]

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        result = simple_agent._call_llm_with_tools("系统", "任务")

        assert "25°C" in result
        assert mock_client.chat.completions.create.call_count == 2

    def test_run_full_cycle(self, simple_agent, mock_client):
        """测试完整的 run() 流程（含 plan → execute → 跳过反思）"""
        simple_agent.mode = "brief"  # brief 模式跳过反思
        simple_agent.reflection = "auto"

        # Plan 阶段
        resp_plan = MagicMock()
        resp_plan.choices = [
            MagicMock(message=MagicMock(content="1. 分析任务\n2. 生成教案"))
        ]

        # Execute 阶段
        resp_exec = MagicMock()
        resp_exec.choices = [
            MagicMock(message=MagicMock(content="# 导数教案\n\n完整教案内容..."))
        ]

        mock_client.chat.completions.create.side_effect = [resp_plan, resp_exec]

        result = simple_agent.run("设计导数教案")

        assert "导数教案" in result
        assert mock_client.chat.completions.create.call_count == 2


# ═══════════════════════════════════════════
# Mode Instructions Tests
# ═══════════════════════════════════════════

class TestModes:
    def test_all_modes_have_instructions(self):
        for mode in ["brief", "standard", "detailed"]:
            assert mode in MODE_INSTRUCTIONS
            assert len(MODE_INSTRUCTIONS[mode]) > 0


# ═══════════════════════════════════════════
# Evaluator Tests
# ═══════════════════════════════════════════

class TestEvaluator:
    def test_score_one_perfect(self):
        """测试一个完美输出的评分"""
        from eduagent.core.evaluator import BenchmarkCase

        case = BenchmarkCase(
            id="test_001",
            task="测试任务",
            agent="lesson_planner",
            min_length=100,
            required_sections=["基本信息", "教学目标"],
            required_keywords=["导数", "切线"],
        )

        output = """# 导数与切线 - 教学设计

## 一、基本信息
- 学段：高中二年级

## 二、教学目标
### 知识与技能
理解导数的几何意义，掌握切线方程的求法
""" + "x" * 200  # 填充长度

        evaluator = Evaluator(cases=[case])
        report = evaluator.score_one(case, output)

        assert report.total > 60
        assert report.details["sections_found"] == 2
        assert report.details["keywords_found"] == 2

    def test_score_one_poor(self):
        """测试一个低质量输出"""
        from eduagent.core.evaluator import BenchmarkCase

        case = BenchmarkCase(
            id="test_002",
            task="测试",
            agent="lesson_planner",
            min_length=500,
            required_sections=["基本信息", "教学目标", "教学重难点"],
            required_keywords=["导数", "极限", "斜率"],
        )

        output = "简短回答，没有结构"

        evaluator = Evaluator(cases=[case])
        report = evaluator.score_one(case, output)

        assert report.total < 50
        assert report.details["sections_found"] == 0

    def test_evaluate_batch(self):
        """测试批量评测"""
        from eduagent.core.evaluator import BenchmarkCase

        case1 = BenchmarkCase(
            id="batch_001", task="t1", agent="lesson_planner",
            min_length=100, required_sections=["教学目标"],
        )
        case2 = BenchmarkCase(
            id="batch_002", task="t2", agent="lesson_planner",
            min_length=100, required_sections=["教学目标"],
        )

        evaluator = Evaluator(cases=[case1, case2])

        def mock_run(task, agent):
            return "# 标题\n## 教学目标\n" + "content " * 30

        results = evaluator.evaluate(mock_run)
        assert results["total_cases"] == 2
        assert results["pass_count"] == 2
        assert results["pass_rate"] == 100.0

    def test_render_report(self):
        evaluator = Evaluator(cases=[])
        results = {
            "total_cases": 1,
            "pass_count": 1,
            "pass_rate": 100.0,
            "avg_score": 85.0,
            "min_score": 85.0,
            "max_score": 85.0,
            "reports": [{
                "case_id": "test",
                "score": 85.0,
                "details": {
                    "length": 500,
                    "dimension_scores": {
                        "completeness": 80, "structure": 90,
                        "accuracy": 85, "actionability": 80,
                        "format": 95,
                    }
                }
            }],
        }
        md = evaluator.render_report(results)
        assert "# EduAgent 评测报告" in md
        assert "85.0" in md
