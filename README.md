# EduAgent

> 🧠 A lightweight multi-agent framework for teaching — Plan → Execute → Reflect, making AI a real participant in instructional design

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com/fengxaios/EduAgent)
[![Release](https://img.shields.io/badge/Release-v1.0.0-blue)](https://github.com/fengxaios/EduAgent/releases/tag/v1.0.0)
[![Tests](https://img.shields.io/badge/Tests-34_passed-green)](https://github.com/fengxaios/EduAgent/actions)
[![Python](https://img.shields.io/badge/Python-3.10_|_3.11_|_3.12-blue)](https://www.python.org/)

🇨🇳 [中文文档](README_CN.md)

## ✨ Highlights

- 🏗️ **Complete Agent Architecture**: Plan → Execute → Reflect three-phase loop with automatic quality control
- 🤝 **Multi-Agent Collaboration**: Intelligent routing + pipeline orchestration for complex teaching workflows
- 🪶 **Lightweight & Self-Built**: Zero dependency on LangChain or other heavy frameworks; core logic under 500 lines
- 🔧 **Flexible Tool System**: OpenAI-compatible Function Calling with a clean decorator-based registration API
- 🧠 **Dual-Channel Memory**: Conversation context (sliding window) + knowledge base (persistent storage)
- 🖼️ **Visual Understanding**: Built-in ImageAnalyzerAgent for OCR, formula recognition, and educational content extraction from images
- 📚 **Education-Specialized**: Five dedicated teaching agents covering lesson planning, quiz generation, knowledge mapping, image analysis, and auto-reporting

## 🏗️ Architecture

```
EduAgent/
├── src/eduagent/                   # Python package
│   ├── __init__.py                 # Top-level exports
│   ├── core/                       # Core Agent framework
│   │   ├── agent.py                # Agent base class (Plan→Execute→Reflect)
│   │   ├── orchestrator.py         # Multi-agent orchestrator
│   │   ├── memory.py               # Dual-channel memory system with persistence
│   │   ├── tools.py                # Tool registry & Function Calling
│   │   └── evaluator.py            # Offline quality evaluation framework
│   ├── agents/                     # Specialized teaching agents
│   │   ├── lesson_planner.py       # Lesson plan generation
│   │   ├── quiz_generator.py       # Hierarchical quiz generation
│   │   ├── knowledge_mapper.py     # Knowledge graph decomposition
│   │   └── image_analyzer.py       # Multi-modal educational image analysis
│   └── outputs/                    # Output templates
├── examples/                       # Usage examples
├── tests/                          # Unit tests
├── app.py                          # Gradio web demo
├── pyproject.toml                  # Package config (pip install -e .)
└── README.md
```

### Agent Lifecycle

```
User Task → [Plan] → [Execute] → [Reflect]
                 ↑                        |
                 └──── iterate if needed ──┘
```

Each agent follows a three-phase loop:
1. **Plan** — Decompose the task into actionable steps
2. **Execute** — Invoke tools or generate content via LLM
3. **Reflect** — Self-evaluate output quality; retry if necessary

Reflection strategy is configurable: `auto` (heuristic-based skip for well-structured outputs), `always`, or `never`.

## 🎬 Quick Demo

### Lesson Plan (brief mode)
```
# Lagrange Mean Value Theorem — Lesson Plan

## Basic Info
- Grade: High School Year 2  |  Duration: 45 min  |  Type: New Lesson

## Teaching Objectives
### Knowledge & Skills
- State the theorem: if f is continuous on [a,b] and differentiable on (a,b),
  then ∃ ξ ∈ (a,b) such that f'(ξ) = [f(b)−f(a)]/(b−a)
- Understand the geometric meaning (tangent parallel to secant)

### Process & Method
- Discover the proof via auxiliary function construction from Rolle's Theorem
- GeoGebra dynamic demo → condition analysis → examples/counter-examples

## Key Points & Strategies
- Key: Theorem conditions, geometric meaning, and application
- Strategy: Dynamic visualization + numerical approximation + physical gesture simulation
```

### Quiz Generation (basic difficulty)
```
# Limits: Arithmetic Operations — Layered Exercises

## Core Review
If lim f(x) = A and lim g(x) = B (finite), then:
lim[f(x)±g(x)] = A±B,  lim[f(x)·g(x)] = AB,  lim[f(x)/g(x)] = A/B (B≠0)

## 1. Basic Practice (12 min)
### 1. [Multiple Choice] Given lim f(x)=4, lim g(x)=−1 as x→0, find lim[f(x)·g(x)+3]
A. −7  B. −1  C. 1  D. 7
> Answer: B  |  Explanation: 4×(−1)+3 = −1

### 2. [Fill-in] lim(x→3) (x²−9)/(x−3) = ___
> Answer: 6  |  Explanation: Factor: (x−3)(x+3)/(x−3) = x+3 → 6
```

### Pipeline Collaboration
```python
from eduagent import Orchestrator, LessonPlannerAgent, QuizGeneratorAgent, KnowledgeMapperAgent, ReporterAgent

orch = Orchestrator()
orch.register_all([KnowledgeMapperAgent(), LessonPlannerAgent(), QuizGeneratorAgent(), ReporterAgent()])

# 4-agent pipeline: knowledge → lesson → quiz → report
results = orch.pipeline([
    {"agent": "knowledge_mapper", "task": "Decompose 'definite integrals' knowledge points"},
    {"agent": "lesson_planner", "task": "Generate a lesson plan based on the decomposition"},
    {"agent": "quiz_generator", "task": "Create 5 practice problems for the lesson"},
    {"agent": "reporter", "task": "Write a pipeline analysis report"},
])
# Outputs a structured report with confidence estimates per agent
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- An API key from a compatible LLM provider (Alibaba Cloud DashScope, OpenAI, DeepSeek, etc.)

### Installation

```bash
git clone https://github.com/fengxaios/EduAgent.git
cd EduAgent
pip install -e .
```

### Configuration

```bash
# Copy the configuration template
cp .env.example .env

# Edit .env with your API key
# DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

EduAgent uses the [OpenAI SDK](https://github.com/openai/openai-python) under the hood and is compatible with **any OpenAI-compatible API endpoint**.

| Provider | Base URL Example |
|----------|-----------------|
| Alibaba DashScope (default) | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Ollama (local) | `http://localhost:11434/v1` |

### Three-Minute Start

```python
from eduagent import Orchestrator, LessonPlannerAgent, QuizGeneratorAgent, KnowledgeMapperAgent

# Initialize (auto-loads .env)
orchestrator = Orchestrator()

# Register agents
orchestrator.register_all([
    LessonPlannerAgent(),
    QuizGeneratorAgent(),
    KnowledgeMapperAgent(),
])

# Intelligent routing: auto-selects the best agent
result = orchestrator.route(
    "Design a lesson plan on 'Derivatives and Tangent Lines' for high school sophomores"
)
print(result['result'])

# Pipeline collaboration: multiple agents working in sequence
results = orchestrator.pipeline([
    {"agent": "knowledge_mapper", "task": "Decompose the knowledge points of 'Definite Integrals'"},
    {"agent": "lesson_planner", "task": "Generate a lesson plan based on the decomposition"},
    {"agent": "quiz_generator", "task": "Create 5 practice problems"},
])
```

## 🧩 Core Agent Types

### 1. LessonPlannerAgent

Generates structured lesson plans with:
- Learning objectives (Knowledge / Skill / Competency)
- Key & difficult points with breakthrough strategies
- Detailed teaching process (Engage → Teach → Practice → Synthesize)
- Board design & homework assignments

| Mode | Description | Approx. Length |
|------|-------------|---------------|
| `brief` | Outline only — key info, objectives, main flow | ~30 lines |
| `standard` | Complete structure with moderate detail | ~60 lines |
| `detailed` | Full activity design with teacher-student interaction scripts | ~100+ lines |

### 2. QuizGeneratorAgent

Generates tiered practice exercises with answers and step-by-step solutions:

| Difficulty | Sections | Ideal Use Case |
|-----------|----------|----------------|
| `basic` | Foundation exercises | In-class practice after concept introduction |
| `intermediate` | Foundation + Skill Building | Homework or unit quiz |
| `advanced` | Skill Building + Challenge | Competition prep or advanced students |
| `all` | All three tiers | Unit review or comprehensive assessment |

Question types: Multiple choice, Fill-in-blank, Problem-solving, Proofs
All answers include step-by-step derivations using LaTeX for math formulas.

### 3. KnowledgeMapperAgent

Decomposes complex knowledge domains into teachable modules:

- **Knowledge Tree**: Hierarchical structure with difficulty ratings (★☆☆ ~ ★★★) and teaching method suggestions
- **Prerequisite Dependencies**: Ordered learning paths (A → B = "must learn A before B")
- **Teaching Routes**: Standard, fast-track, and deep-learning paths
- **Common Misconceptions**: Specific student errors with correction strategies

### 4. ImageAnalyzerAgent 🆕 v0.2.0

Multi-modal agent for educational image analysis:

- **OCR text extraction**: Printed materials, handwritten notes, blackboard shots
- **Subject & knowledge point identification**: Automatic classification by discipline and grade level
- **Formula recognition**: Outputs standard LaTeX for mathematical expressions
- **Structured analysis**: Difficulty assessment, teaching suggestions, misconception warnings
- **Multi-mode output**: `brief` (OCR only), `standard` (structured analysis), `detailed` (full teaching analysis)

```python
from eduagent import ImageAnalyzerAgent, Orchestrator

orchestrator = Orchestrator()
agent = ImageAnalyzerAgent(vision_model="qwen-vl-plus")
orchestrator.register(agent)

result = orchestrator.route(
    "Analyze this exam paper for knowledge points and difficulty",
    images=["path/to/exam_paper.jpg"]
)
```

## 🔧 Extending with Custom Agents

Creating a custom agent is as simple as defining a system prompt:

```python
from eduagent import Agent

class MathTutorAgent(Agent):
    def get_system_prompt(self) -> str:
        return """You are an expert mathematics tutor specializing in calculus.
Your responses should be step-by-step and pedagogical."""

# Register and use
orchestrator.register(MathTutorAgent(name="math_tutor"))
```

## 🛠️ Tool System

Register external functions as callable tools using the decorator API:

```python
from eduagent import Agent, ToolRegistry

registry = ToolRegistry()

@registry.register(name="calculate", description="Evaluate a mathematical expression")
def calculate(expression: str):
    return eval(expression)

agent = LessonPlannerAgent(tools=registry)
```

Tools are automatically serialized to OpenAI Function Calling schemas, enabling LLMs to invoke them during task execution.

## 🧪 Evaluation Framework

The built-in **Evaluator** provides offline, rule-based quality scoring without additional LLM calls — useful for regression testing and CI integration:

```python
from eduagent import Evaluator

evaluator = Evaluator()

def run_fn(task, agent_name):
    return orchestrator.agents[agent_name].run(task)

results = evaluator.evaluate(run_fn)
print(evaluator.render_report(results))
```

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Completeness | 30% | Required section coverage |
| Structure | 20% | Markdown hierarchy quality |
| Accuracy | 25% | Keyword & concept coverage |
| Actionability | 15% | Output usability (no filler text) |
| Format | 10% | Title/list/table formatting |

## 📦 Memory System

```
┌─────────────────────────────────┐
│         Dual-Channel Memory     │
├──────────────┬──────────────────┤
│ Conversation │ Knowledge Base   │
│ (sliding win)│ (persistent KV)  │
├──────────────┼──────────────────┤
│ • Context    │ • Facts          │
│ • History    │ • Preferences    │
│ • Auto-trim  │ • Searchable     │
└──────────────┴──────────────────┘
```

```python
from eduagent import Memory

# Save memory to disk
memory = Memory()
memory.set_knowledge("favorite_style", "detailed lesson plans")
memory.save("session_memory.json")

# Restore later
restored = Memory.load("session_memory.json")
```

## 🌐 Web Demo

Launch the Gradio-based web interface:

```bash
pip install gradio
python app.py
```

Features:
- 🎯 **Single Agent Mode**: Select agent, task, mode, and difficulty
- 🔗 **Pipeline Mode**: Chain knowledge_mapper → lesson_planner → quiz_generator
- ℹ️ **System Status**: View registered agents and configuration

The demo launches at `http://localhost:7860`.

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

34 unit tests covering agent lifecycle, orchestrator routing, memory persistence, tool registration, and evaluation scoring.

## 🗺️ Roadmap

- [x] Core Agent framework (Plan → Execute → Reflect)
- [x] Multi-agent orchestrator (routing + pipeline)
- [x] Dual-channel memory with persistence
- [x] Tool system (Function Calling)
- [x] Lesson Planner, Quiz Generator, Knowledge Mapper agents
- [x] Offline evaluator
- [x] ImageAnalyzerAgent (v0.2.0)
- [x] Gradio web demo
- [ ] Multi-LLM provider auto-detection
- [ ] Langfuse / Weave tracing integration
- [ ] RAG-enhanced knowledge base
- [ ] Learning path auto-generation
- [ ] Student assessment & progress tracking

## 🤝 Contributing

Contributions are welcome! This project participates in the [MetaX Youth Open Source Seed Fund Program](https://mp.weixin.qq.com/s/tJ4KRSR-hQTeJN7zGsqLOw).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [MetaX（沐曦股份）](https://www.metax-tech.com/) & [CCF](https://www.ccf.org.cn/) — Youth Open Source Fund Program
- [Alibaba Cloud DashScope](https://dashscope.aliyun.com/) — LLM API support
- The open-source education community
