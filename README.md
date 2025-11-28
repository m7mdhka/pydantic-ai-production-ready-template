# Pydantic AI Production Ready Template

A production-ready template for building applications with Pydantic AI, FastAPI, and modern Python tooling.

## Requirements

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

Install project dependencies:

```bash
make install
```

For development, install with dev dependencies:

```bash
make install-dev
```

## Development Setup

### Pre-commit Hooks

Pre-commit won't run automatically until you actually install the hooks into `.git/hooks`. Run the installer once (it's not in git history) so Git knows to invoke them:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

After that, every `git commit` will trigger the lint/format checks plus the Commitizen commit-msg hook from your `.pre-commit-config.yaml`. If you ever need to lint everything manually, use:

```bash
uv run pre-commit run --all-files
```

Alternatively, you can use the Makefile targets:

```bash
make pre-commit-install  # Install pre-commit hooks
make pre-commit-run      # Run pre-commit hooks on all files
```

## Available Commands

Run `make help` to see all available commands, or use:

- `make install` - Install project dependencies
- `make install-dev` - Install project dependencies including dev dependencies
- `make run` - Run the application in production mode
- `make run-dev` - Run the application in development mode with auto-reload
- `make format` - Format code using Ruff
- `make test` - Run tests using pytest
- `make test-cov` - Run tests with coverage report
- `make docker-dev-up` - Start development Docker services
- `make docker-dev-down` - Stop development Docker services
- `make migration-create MESSAGE="message"` - Create a new migration
- `make migration-upgrade` - Upgrade database to the latest migration

## License

[Add your license here]
