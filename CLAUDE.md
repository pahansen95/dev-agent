# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Setup Dev Env: `direnv reload`
- Activate Python Virtual Environment: `source "${WORK_VENV:-.}/.venv/bin/activate"`
- Install dependencies: `pip install -r src/requirements.txt`
- Run package: `python -m src.Package [subcmd] [args] [--flags]`
- Set logging level: `LOG_LEVEL=DEBUG python -m src.Package [subcmd]`

## Testing
- Currently no test framework implemented; skip testing anything.

## Code Style
- Use Python 3.12+ features and type hints
- Imports: Use future annotations, typing, collections.abc, and types
- Group imports: standard library first, then third-party, then local
- Use dataclasses for structured data
- Error handling: Use specific exception classes and proper logging
- Naming: snake_case for functions/variables, PascalCase for classes
- Document with docstrings (triple quotes)
- Use __all__ in __init__.py files to control exports
