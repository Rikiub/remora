[doc('List available recipes')]
default:
    @just --list

# ==============================
# Application
# ==============================

temp_dir := "tmp/"

[positional-arguments]
[doc('Run CLI app isolated in tmp/ directory')]
[group("app")]
run *args:
    @mkdir -p {{ temp_dir }}
    @cd {{ temp_dir }}
    
    -@uv run remora "$@"

# ==============================
# Environment
# ==============================

[doc('Sync dependencies and set up the virtual environment')]
[group("env")]
setup:
    uv sync

[doc('Upgrade all dependencies to their latest versions based on pyproject.toml')]
[group('env')]
upgrade:
    uv lock --upgrade
    uv sync

# ==============================
# Maintenance
# ==============================

[doc('Clean cache directories, bytecode, and temp files')]
[group("maintenance")]
clean:
    # Clean tool caches
    rm -rf .ruff_cache/
    rm -rf .pytest_cache/
    
    # Clean project temp folders
    rm -rf tmp/
    
    # Clean build artifacts
    rm -rf build/ dist/ *.egg-info/
    
    # Clean Python bytecode 
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete


# ==============================
# Testing
# ==============================

alias test := test-unit

[doc('Run integration tests with pytest')]
[group('test')]
test-integration *args:
    uv run pytest -m "integration" {{ args }}

[doc('Run unit tests with pytest')]
[group('test')]
test-unit *args:
    uv run pytest {{ args }}

# ==============================
# Code Quality & Formatting
# ==============================

[doc('Format code with Ruff')]
[group('quality')]
format:
    uv run ruff format .

[doc('Lint code and apply safe fixes with Ruff')]
[group('quality')]
lint:
    uv run ruff check . --fix

[doc('Run static type checking and apply fixes with ty')]
[group('quality')]
type:
    uv run ty check --fix

[doc('Run all formatting and apply safe fixes (formatting, linting, types)')]
[group('quality')]
fix: format lint type

[doc('Run all quality checks without changes (formatting, linting, types, unit tests)')]
[group('quality')]
check:
    # Format
    uv run ruff format --check .

    # Lint
    uv run ruff check .

    # Type check
    uv run ty check

    # Run tests
    uv run pytest
