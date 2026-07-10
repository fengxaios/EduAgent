# Contributing to EduAgent

Thanks for your interest in contributing! Here's how to get started.

## Quick Start

```bash
git clone https://github.com/fengxaios/EduAgent.git
cd EduAgent
pip install -e ".[dev]"
```

## Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev,demo]"

# Run tests
pytest tests/ -v

# Run CLI
python -m eduagent status
```

## Project Structure

```
src/eduagent/
├── core/          # Agent base class, orchestrator, memory, tools
├── agents/        # Teaching agents (lesson, quiz, knowledge, image, reporter)
├── outputs/       # Output templates
├── cli.py         # CLI entry point
└── __main__.py    # python -m eduagent support
```

## Adding a New Agent

1. Create `src/eduagent/agents/your_agent.py`
2. Subclass `Agent` and implement `get_system_prompt()`
3. Export from `agents/__init__.py` and top-level `__init__.py`

```python
from eduagent import Agent

class YourAgent(Agent):
    def get_system_prompt(self) -> str:
        return "You are an expert in ..."

    def __init__(self, **kwargs):
        super().__init__(name="your_agent", **kwargs)
```

## Code Style

- Type hints on all public methods
- Docstrings for all public classes and functions
- Line length: 100 chars max
- Python 3.10+ compatible

## Testing

```bash
pytest tests/ -v
pytest tests/ -v --cov=eduagent  # with coverage
```

Write tests for new agents and core functionality.

## Commit Convention

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code restructuring
- `test:` tests
- `chore:` maintenance

## License

Apache 2.0. All contributions are under the same license.
