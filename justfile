set positional-arguments

[doc('List available recipes')]
default:
    @just --list

# ==============================
# Application
# ==============================

_temp_dir := "tmp/"

[doc('Run CLI app isolated in tmp/ directory')]
[group("app")]
run *args:
    @mkdir -p {{ _temp_dir }}
    -@cd {{ _temp_dir }} && uv run remora "$@"

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
    -rm -rf .ruff_cache/
    -rm -rf .pytest_cache/
    
    # Clean project temp folders
    -rm -rf tmp/
    
    # Clean build artifacts
    -rm -rf build/ dist/ *.egg-info/
    
    # Clean Python bytecode 
    -find . -type d -name "__pycache__" -exec rm -rf {} +
    -find . -type f -name "*.pyc" -delete


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
format *args:
    uv run ruff format . {{ args }}

[doc('Lint code with Ruff')]
[group('quality')]
lint *args:
    uv run ruff check . {{ args }}

[doc('Type check code with ty')]
[group('quality')]
type *args:
    uv run ty check {{ args }}

[doc('Run all formatting and apply safe fixes (formatting, linting, types)')]
[group('quality')]
fix: format (lint "--fix") (type "--fix")

[doc('Run all quality checks without changes (formatting, linting, types, unit tests)')]
[group('quality')]
check: (format "--check") lint type test-unit