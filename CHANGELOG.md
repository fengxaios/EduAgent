# Changelog

All notable changes to EduAgent will be documented in this file.

## [0.2.0] - 2026-07-07

### Added
- **ImageAnalyzerAgent**: Multi-modal agent for educational image analysis supporting OCR text extraction, formula recognition (LaTeX output), subject/knowledge point identification, and structured teaching analysis in three output modes (brief/standard/detailed)
- **Vision LLM support** in Agent base class (`_encode_image`, `_call_llm_vision`) with automatic base64 encoding and large-image warnings
- **Auto .env discovery** from package location in Orchestrator
- **Bilingual documentation**: English README.md + Chinese README_CN.md

### Changed
- `__init__.py` now exports `ImageAnalyzerAgent` and `Evaluator`

## [0.1.0] - 2026-07-03

### Added
- **Agent base class** with Plan → Execute → Reflect three-phase loop
- **Multi-agent orchestrator** with intelligent routing and pipeline collaboration
- **Dual-channel memory system**: conversation context + knowledge base with persistence
- **Tool registry** with OpenAI Function Calling schema support
- **Output quality evaluator** (Evaluator)
- **Lesson Planner Agent**: structured lesson plan generation with mode control (brief/standard/detailed)
- **Quiz Generator Agent**: layered quiz generation with difficulty control (basic/intermediate/advanced/all)
- **Knowledge Mapper Agent**: knowledge point decomposition with 4 mandatory sections (tree + dependencies + routes + pitfalls)
- **Output templates** for lesson plans, quizzes, and PPT outlines
- **Smart reflection skip**: heuristic-based reflection for well-structured outputs
- **Auto strip** of ```markdown wrappers from LLM outputs
- **Standard Python package** layout (`src/eduagent/`) with `pyproject.toml`
- **pip install -e .** one-command installation
- **Auto .env discovery** from package location
- **Gradio web interface** (app.py)

### Technical
- Python 3.10+ with OpenAI SDK
- Alibaba Cloud DashScope (qwen-plus) as default LLM
- Lightweight self-built framework — zero dependency on LangChain
- 34 unit tests (pytest)
- Apache 2.0 License

[0.1.0]: https://github.com/fengxaios/EduAgent/releases/tag/v0.1.0
