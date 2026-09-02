set windows-shell := ["cmd.exe", "/c"]

[doc('List available recipes')]
default:
    @just --list

# ==============================
# Application
# ==============================

_temp_dir := "tmp"
_run_doc := 'Run CLI app isolated in tmp/ directory'

[doc(_run_doc)]
[group("app")]
[positional-arguments]
[unix]
run *args:
    -@mkdir {{ _temp_dir }}
    -@cd {{ _temp_dir }}
    -@uv run remora "$@"

[doc(_run_doc)]
[group("app")]
[positional-arguments]
[windows]
run *args:
    #!powershell -NoProfile
    if (!(Test-Path "{{ _temp_dir }}")) { $null = mkdir "{{ _temp_dir }}" }
    cd "{{ _temp_dir }}"
    uv run remora $args

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
# Docs
# ==============================

_zensical_config := 'packages/docs/zensical.toml'

[doc('Serve documentation site')]
[group('docs')]
docs-serve:
    uv run zensical serve --config-file {{ _zensical_config }}

[doc('Build documentation site')]
[group('docs')]
docs-build:
    uv run zensical build --config-file {{ _zensical_config }}

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
    uv run python -m pytest -m "integration" {{ args }}

[doc('Run unit tests with pytest')]
[group('test')]
test-unit *args:
    uv run python -m pytest {{ args }}

# ==============================
# Code Quality & Formatting
# ==============================

[doc('Format code with Ruff')]
[group('quality')]
format *args:
    -uv run ruff format . {{ args }}

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
