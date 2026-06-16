---
id: be7e5452-d861-475d-8da8-c82bc4bbd9c4
slug: run-tests
title: Test Runner Script
source: ../run_tests.py
domain: technical
tags: [kbi, testing, pytest, test-runner, python]
created: 2026-06-11
updated: 2026-06-11
---

# Test Runner Script

> CLI wrapper around pytest that organizes tests into five named suites (quick, unit, integration, all, coverage) with dependency checking and project-directory anchoring.

## Core Concepts

- **Suite taxonomy**:
	- `quick` — `tests/test_quick_commit.py`, `--tb=short` (< 30s, development feedback)
	- `unit` — `tests/unit/`, `--tb=short` (< 2min, component-level)
	- `integration` — `tests/integration/`, `--tb=long` (< 5min, full workflow)
	- `all` — runs quick → unit → integration in sequence, reports per-suite pass/fail
	- `coverage` — runs all tests under `coverage run`, then `coverage report -m` + HTML in `htmlcov/`
- **Dependency check**: validates `pytest`, `pyyaml`, `jsonschema` importable before running; directs to `requirements.txt` on failure
- **Project-dir anchor**: `os.chdir(Path(__file__).parent)` ensures tests run from the project root regardless of caller CWD
- **Coverage auto-install**: installs `coverage` via pip if missing before the coverage suite
