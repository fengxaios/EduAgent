# EduAgent v1.0.0 🎉

> Production-ready multi-agent framework for teaching scenarios.
> Plan → Execute → Reflect | 5 Agents | CLI + API

## What's New in v1.0.0

### CLI Interface
```bash
# After pip install:
eduagent lesson "导数的几何意义" --mode brief
eduagent quiz "极限四则运算" --difficulty basic
eduagent pipeline "定积分"

# Or without install:
python -m eduagent lesson "Lagrange Mean Value Theorem"
```

### Production Ready
- Development Status: Production/Stable
- 34 tests passing
- Full type hints on public APIs
- OSI-approved Apache 2.0 license
- `pip install eduagent` (coming to PyPI)

### 5 Specialized Agents

| Agent | Capability | Output |
|-------|-----------|--------|
| LessonPlanner | Full lesson plans | 3 modes (brief/standard/detailed) |
| QuizGenerator | Layered exercises | 4 difficulty levels |
| KnowledgeMapper | Knowledge graphs | Tree + dependencies + routes |
| ImageAnalyzer | OCR + formula recognition | LaTeX output |
| ReporterAgent | Pipeline reports | Confidence estimation |

### Architecture
```
Orchestrator → Agent → Plan → Execute → Reflect
                   ↕ StructuredProtocol (AgentMessage)
                   ↕ Memory (conversation + knowledge)
```

### Quick Install
```bash
git clone https://github.com/fengxaios/EduAgent.git
cd EduAgent
pip install -e .
eduagent status
```

## Links
- GitHub: https://github.com/fengxaios/EduAgent
- Docs: README.md (EN) + README_CN.md (中文)
- CHANGELOG: [CHANGELOG.md](CHANGELOG.md)

---

1,800+ lines Python | 14 source files | 34 tests | Apache 2.0
