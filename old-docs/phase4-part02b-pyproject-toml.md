# Phase 4 — Part 02b: Tool Configuration (pyproject.toml)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02b |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — FastAPI Foundation |
| **File** | `backend/pyproject.toml` |
| **Depends On** | Part 02a (requirements.txt — tools are installed from there) |
| **Next** | [Part 02c — Dockerfile](./phase4-part02c-dockerfile-backend.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~8 minutes |
| **Lines** | ~55 lines |

---

## What is pyproject.toml? Read This First

`pyproject.toml` is the **configuration hub** for all your Python development tools. Instead of having separate config files for each tool:

```
WITHOUT pyproject.toml:
├── .flake8          (linting config)
├── mypy.ini         (type checking config)
├── pytest.ini       (testing config)
├── .coveragerc      (coverage config)
└── setup.cfg        (more config)

WITH pyproject.toml:
└── pyproject.toml   (ALL tool configs in ONE file)
```

**Real-world analogy:** Instead of having separate instruction manuals for your oven, fridge, and dishwasher, you have one house manual with sections for each appliance.

### What Tools Do We Configure?

| Tool | What It Does | Why |
|------|-------------|-----|
| **Ruff** | Lints (finds problems) and formats code | 100x faster than flake8+black combined |
| **MyPy** | Checks type hints are correct | Catches type bugs before runtime |
| **Pytest** | Runs tests, reports results | The standard Python test framework |
| **Coverage** | Measures which code lines tests cover | Aim for 70%+ coverage |

---

## Source Code — Line by Line

> 📁 **File:** `backend/pyproject.toml`
> 📏 **Lines:** ~55
> ⏱️ **Type time:** ~8 minutes

```toml
[project]
name = "health-tracker"
version = "1.0.0"
description = "AI-Powered Personal Health & Habit Tracker"
requires-python = ">=3.11"

# ── Ruff (Linter + Formatter) ──
# Ruff replaces flake8, black, isort — 10-100x faster because it's written in Rust
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
# Rules we enforce:
# E = pycodestyle errors (basic style)
# F = pyflakes (unused imports, undefined names)
# I = isort (import sorting)
# N = pep8-naming (function_names, ClassName)
# UP = pyupgrade (use modern Python syntax)
# B = bugbear (common bugs)
# SIM = simplify (simpler code patterns)
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
ignore = [
    "E501",   # Line too long — we set line-length above, ruff formatter handles this
    "B008",   # Do not perform function call in argument defaults — FastAPI uses Depends()
]

[tool.ruff.lint.isort]
known-first-party = ["app"]

# ── MyPy (Type Checker) ──
# Catches type errors at development time, not production runtime
[tool.mypy]
python_version = "3.11"
strict = false
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
plugins = ["pydantic.mypy"]

# ── Pytest ──
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (needs DB + Redis)",
    "slow: Slow tests (AI calls, large data)",
]
asyncio_mode = "auto"

# ── Coverage ──
[tool.coverage.run]
source = ["app"]
omit = [
    "app/tasks/*",
    "alembic/*",
]

[tool.coverage.report]
show_missing = true
fail_under = 70
```

**Key lines explained:**

- **`select = ["E", "F", "I", "N", "UP", "B", "SIM"]`** — 7 rule categories. Each letter is a ruleset:
  - `E` catches: `if x == True:` (should be `if x:`)
  - `F` catches: unused imports, undefined variables
  - `I` sorts imports: stdlib → third-party → local
  - `B` catches: mutable default arguments, except bare Exception

- **`ignore = ["E501", "B008"]`** — Two exceptions:
  - `E501` (line too long): Ruff formatter handles line wrapping, no need for the linter to flag it
  - `B008` (function call in defaults): FastAPI's `Depends()` is designed to be used as a default argument — this is intentional, not a bug

- **`asyncio_mode = "auto"`** — pytest-asyncio automatically handles async test functions. Without this, you'd need `@pytest.mark.asyncio` on every async test.

- **`fail_under = 70`** — If test coverage drops below 70%, the coverage report fails. This prevents gradually losing test coverage.

---

## How This Connects

```
pyproject.toml
     │
     ├── ruff check app/       ← runs before every commit (pre-commit hook)
     ├── mypy app/              ← runs in CI/CD pipeline
     ├── pytest tests/          ← runs locally and in CI
     └── pytest --cov=app       ← coverage report
```

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | pyproject.toml | Single config file for all Python dev tools |
| 2 | Ruff | Ultra-fast linter + formatter (replaces flake8 + black + isort) |
| 3 | MyPy | Static type checker — catches type bugs before runtime |
| 4 | Pytest markers | Categorize tests: unit, integration, slow |
| 5 | Coverage threshold | Fail if tests cover < 70% of code |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `B008 Do not perform function calls in argument defaults` | Using `Depends()` in FastAPI | Add `"B008"` to the `ignore` list |
| `Module "app" has no attribute "X"` (mypy) | Missing type stubs for third-party lib | Add `ignore_missing_imports = true` |
| `asyncio_mode not found` | Old pytest-asyncio version | `pip install pytest-asyncio>=0.24` |

---

## 🎤 Interview Q&A

### Q: "How do you ensure code quality in your project?"

> "Three tools configured in pyproject.toml. Ruff for linting and formatting — it's 100x faster than flake8 because it's written in Rust. It catches unused imports, style issues, and common bugs. MyPy for static type checking — catches type errors at development time, not production. Pytest with 70% minimum coverage threshold — if tests cover less than 70% of the codebase, the CI pipeline fails. All three run in the GitHub Actions CI pipeline: lint → test → build."

### Q: "Why Ruff instead of flake8 + black?"

> "Speed and simplicity. Ruff is one tool that replaces flake8 (linting), black (formatting), and isort (import sorting). It's written in Rust and runs 10-100x faster — linting the entire backend takes 0.1 seconds instead of 5 seconds. For CI/CD pipelines where you pay per minute, that adds up. It also means one config section instead of three separate config files."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02a — requirements.txt](./phase4-part02a-requirements.md) | | [Part 02c — Dockerfile](./phase4-part02c-dockerfile-backend.md) |
