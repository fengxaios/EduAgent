# EduAgent

> 🧠 面向教学场景的轻量级多智能体框架 — 规划 → 执行 → 反思，让 AI 真正参与教学设计

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

## ✨ 亮点

- 🏗️ **完整 Agent 架构**：规划(Plan) → 执行(Execute) → 反思(Reflect) 三阶段循环
- 🤝 **多 Agent 协作**：智能路由 + 管线编排，多个 Agent 串行完成复杂教学任务
- 🪶 **轻量级自研**：不依赖 LangChain 等重型框架，核心代码 < 500 行
- 🔧 **工具系统**：灵活的 Function Calling 注册机制，Agent 可调用外部工具
- 🧠 **双通道记忆**：对话上下文 + 知识库，越用越聪明
- 📚 **教学专项**：教案设计、习题生成、知识点拆解三大教学 Agent 开箱即用

## 🏗️ 架构

```
EduAgent/
├── src/eduagent/              # Python 包
│   ├── __init__.py            # 顶层导出
│   ├── core/                  # Agent 核心框架
│   │   ├── agent.py           # Agent 基类（规划/执行/反思）
│   │   ├── orchestrator.py    # 多 Agent 编排器
│   │   ├── memory.py          # 双通道记忆系统
│   │   └── tools.py           # 工具注册与调用
│   ├── agents/                # 教学专项 Agent
│   │   ├── lesson_planner.py  # 教案设计
│   │   ├── quiz_generator.py  # 习题生成
│   │   └── knowledge_mapper.py # 知识点拆解
│   └── outputs/               # 输出模板
├── examples/                  # 使用示例
├── tests/                     # 单元测试
├── pyproject.toml             # 包配置 (pip install -e .)
└── README.md
```

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/fengxaios/EduAgent.git
cd EduAgent
pip install -e .
```

### 配置

```bash
# 复制配置模板
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

支持任何兼容 OpenAI API 的 LLM 服务（阿里云百炼、DeepSeek、OpenAI 等）。

### 三分钟上手

```python
from eduagent import Orchestrator, LessonPlannerAgent, QuizGeneratorAgent, KnowledgeMapperAgent

# 初始化（自动读取 .env）
orchestrator = Orchestrator()

# 注册 Agent
orchestrator.register_all([
    LessonPlannerAgent(),
    QuizGeneratorAgent(),
    KnowledgeMapperAgent(),
])

# 智能路由：自动选择合适的 Agent
result = orchestrator.route("为高二设计一节「导数与切线」的教案")
print(result['result'])

# 管线协作：多个 Agent 串行工作
results = orchestrator.pipeline([
    {"agent": "knowledge_mapper", "task": "拆解「定积分」知识点"},
    {"agent": "lesson_planner", "task": "生成定积分教案"},
    {"agent": "quiz_generator", "task": "出5道配套练习题"},
])
```

## 🧩 扩展自定义 Agent

```python
from eduagent import Agent

class MyAgent(Agent):
    def get_system_prompt(self) -> str:
        return "你是一个擅长XXX的助手"

# 注册到编排器即可
my_agent = MyAgent(name="my_agent")
orchestrator.register(my_agent)
```

## 📋 参与贡献

欢迎 PR！本项目参加 [沐曦青年开源专项基金种子计划](https://mp.weixin.qq.com/s/tJ4KRSR-hQTeJN7zGsqLOw)，目标构建最实用的教学 Agent 框架。

## 📄 许可

Apache License 2.0 — 详见 [LICENSE](LICENSE)
