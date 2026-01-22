# sg-engine

Offline AI Coach for Smart Guitar — Groove Layer Intelligence

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src/

# Type check
uv run pyright src/sg_engine/
```

## CLI Usage

```bash
# Run coaching job
uv run sg-coach run-job --in context.json --out draft.json

# Validate schemas
uv run sg-coach validate --context context.json
```

## Development

```bash
# Format code
uv run ruff format src/

# Fix lint issues
uv run ruff check --fix src/
```
