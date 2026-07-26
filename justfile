[doc('List available recipes')]
default:
    @just --list

# ==============================
# Environment
# ==============================

[group("env")]
[doc('Sync dependencies and set up the virtual environment')]
setup:
    uv sync

[group('env')]
[doc('Upgrade all dependencies to their latest versions based on pyproject.toml')]
upgrade:
    uv lock --upgrade
    uv sync

# ==============================
# Testing
# ==============================

alias test := test-unit

[group('test')]
[doc('Run integration tests with pytest')]
test-integration *args:
    uv run pytest -m "integration" {{ args }}

[group('test')]
[doc('Run unit tests with pytest')]
test-unit *args:
    uv run pytest {{ args }}

# ==============================
# Code Quality & Formatting
# ==============================

[group('quality')]
[doc('Format code with Ruff')]
format:
    uv run ruff format .

[group('quality')]
[doc('Lint code with Ruff and apply safe fixes')]
lint:
    uv run ruff check . --fix

[group('quality')]
[doc('Run static type checking and apply fixes with ty')]
type:
    uv run ty check --fix

[group('quality')]
[doc('Run all formatting and apply safe fixes (formatting, linting, types)')]
fix: format lint type

[group('quality')]
[doc('Run all quality checks without changes (formatting, linting, types, unit tests)')]
check:
    uv run ruff format --check .
    uv run ruff check .
    uv run ty check
    uv run pytest