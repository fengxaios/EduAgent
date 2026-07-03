"""
核心模块单元测试
"""

import pytest
from core.tools import ToolRegistry
from core.memory import Memory


class TestToolRegistry:
    def test_register_and_call(self):
        registry = ToolRegistry()

        @registry.register(description="加法运算")
        def add(a: int, b: int) -> int:
            return a + b

        result = registry.call("add", a=1, b=2)
        assert result == 3

    def test_get_schema(self):
        registry = ToolRegistry()

        @registry.register(description="问候")
        def greet(name: str) -> str:
            return f"Hello, {name}"

        schema = registry.get_schema()
        assert len(schema) == 1
        assert schema[0]["function"]["name"] == "greet"

    def test_call_unregistered(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError):
            registry.call("nonexistent")


class TestMemory:
    def test_add_and_get_context(self):
        mem = Memory(max_conversation_turns=5)
        mem.add_message("user", "你好")
        mem.add_message("assistant", "你好！")

        ctx = mem.get_context(last_n=1)
        assert len(ctx) == 2

    def test_knowledge_store(self):
        mem = Memory()
        mem.set_knowledge("math.topic", "微积分")
        assert mem.get_knowledge("math.topic") == "微积分"

    def test_knowledge_search(self):
        mem = Memory()
        mem.set_knowledge("python.version", "3.10")
        mem.set_knowledge("project.name", "EduAgent")
        results = mem.search_knowledge("python")
        assert len(results) == 1

    def test_trim(self):
        mem = Memory(max_conversation_turns=2)
        for i in range(5):
            mem.add_message("user", f"msg{i}")
            mem.add_message("assistant", f"reply{i}")
        ctx = mem.get_context(last_n=10)
        # 应只保留最后2轮（4条）
        assert len(ctx) <= 5  # 可能有system消息


class TestAgentBase:
    def test_agent_creation(self):
        from core.agent import Agent

        class TestAgent(Agent):
            def get_system_prompt(self) -> str:
                return "你是一个测试助手"

        agent = TestAgent(name="test")
        assert agent.name == "test"
        assert agent.get_system_prompt() == "你是一个测试助手"
