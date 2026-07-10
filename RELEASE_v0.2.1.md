# EduAgent v0.2.1

> 🧠 面向教学场景的轻量级多智能体框架 | A lightweight multi-agent framework for teaching

## What's New in v0.2.1

### Structured Communication Protocol
Agent-to-agent JSON messaging inspired by PentAGI:
- `AgentMessage`: task → status → artifact → confidence pipeline
- `PipelineReport`: auto-generated cross-analysis with heuristic confidence estimation

### ReporterAgent
Automatic pipeline output aggregation into structured Markdown reports — no more manually stitching agent outputs together.

### Pipeline Experiment
`examples/pipeline_experiment.py` demonstrates 4-agent collaboration:
```
KnowledgeMapper → LessonPlanner → QuizGenerator → ReporterAgent
```

### 5 Agents Total
| Agent | Capability |
|-------|-----------|
| LessonPlanner | Lesson plans (3 output modes) |
| QuizGenerator | Layered quizzes (4 difficulty levels) |
| KnowledgeMapper | Knowledge tree + teaching routes |
| ImageAnalyzer | OCR, formula recognition (LaTeX) |
| ReporterAgent | Auto pipeline reports |

## Install

```bash
git clone https://github.com/fengxaios/EduAgent.git
cd EduAgent
pip install -e .
```

## Links
- GitHub: https://github.com/fengxaios/EduAgent
- CHANGELOG: https://github.com/fengxaios/EduAgent/blob/master/CHANGELOG.md
- Docs (CN): https://github.com/fengxaios/EduAgent/blob/master/README_CN.md

---

34 tests passing | 1,400+ lines Python | Apache 2.0 | No LangChain dependency
