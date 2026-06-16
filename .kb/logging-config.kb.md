---
id: c40b82ef-4ae5-4ac3-a25d-be63b9cf90d3
slug: logging-config
title: Logging Configuration
source: ../logging_config.py
domain: technical
tags: [kbi, logging, python, architecture]
created: 2026-06-11
updated: 2026-06-11
---

# Logging Configuration

> `logging_config.py` provides a dual-destination logging facility (`AppLogger`) with a DEBUG-level file sink auto-created in `/tmp` and a configurable console level, plus a `LoggedOperation` context manager for timed operations.

## Core Concepts

- **`AppLogger`** (class-level state): `setup_logging()` initializes console + file handlers once; subsequent calls are no-ops
- **Dual output**: console level configurable (`WARNING` by default, `DEBUG` via `--debug`); file handler always captures DEBUG to `/tmp/kbi_debug_<timestamp>_<pid>.log` for issue reproduction
- **`get_logger(component)`**: returns a `kbi.<component>` logger (e.g. `kbi.search`); auto-initializes if needed
- **Structured helpers**
	- `log_algorithm_step(name, step, details)` — marks key decision points
	- `log_performance_metric(name, op, duration_ms)` — timing records
	- `log_error_context(name, error, context, op)` — error + full context dict
- **`LoggedOperation` context manager**: records start time; on exit logs performance metric (success) or error context (exception); used throughout `kbi.py` to bracket major operations
- **`create_component_logger(name)`**: convenience wrapper returning `AppLogger.get_logger(name)`
