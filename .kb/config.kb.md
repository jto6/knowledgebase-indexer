---
id: 22d86247-01ec-40ac-aabd-5bb014c50553
slug: config
title: Configuration Management
source: ../config.py
domain: technical
tags: [kbi, configuration, python, architecture]
created: 2026-06-11
updated: 2026-06-11
---

# Configuration Management

> `config.py` provides `ConfigLoader`, which discovers, parses, validates against a JSON schema, and merges kbi YAML/JSON configuration files with built-in defaults.

## Core Concepts

- **Discovery order** (first match wins): explicit `--config` path → `configs/kbi.yml` → `config/kbi.yml` → `kbi.yml` → `~/.config/kbi/config.yml`
- **Schema validation**: `jsonschema` validates the loaded config against `config_schema.json`; `types` block may not have both `include` and `exclude` simultaneously
- **`_normalize_enums()`**: YAML parsers coerce unquoted `on`/`off` to Python booleans; this step converts them back to the string enums the schema expects for `output.partition_by_domain` and `output.views.*`
- **Merge with defaults**: default includes `src/`, `docs/`, `.`; empty keyword list; `freeplane` output format; user config overlays these shallowly; `types` block is passed through as-is
- **`types` selection**: `include` (whitelist) or `exclude` (blacklist) selects which built-in file type handlers are active; absence means all types are active
