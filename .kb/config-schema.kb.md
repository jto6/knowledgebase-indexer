---
id: e8f31501-0bc4-4950-ae8a-b3ee7aaa83c4
slug: config-schema
title: KBI Configuration Schema
source: "[config_schema.json](<../config_schema.json>)"
domain: technical
tags: [kbi, configuration, schema, validation, json-schema]
builds_on: config
created: 2026-06-11
updated: 2026-06-16
---

# KBI Configuration Schema

> `config_schema.json` is the JSON Schema draft-07 contract for `kbi.yml`, enforcing required fields and the full set of allowed options across directories, keywords, output format, view-emission toggles, and indexed file-type selectors.

## Core Concepts

- **Root constraint**: `required: [directories]`; all other top-level keys are optional
- **`directories`**
	- `include` — required array of glob patterns (min 1); specifies directories to index
	- `exclude` — optional array of glob patterns (default `[]`); prunes matched directories
- **`keywords.files`** — optional array; each item is either a plain path string (global, applies to all domains) or a `{path, domain}` object (domain-scoped); `domain` may be a single string or a list of strings (`minItems: 1`); domain-scoped files are loaded only when the current partition's domain matches
- **`output`**
	- `file` — output file path
	- `format` — `freeplane` (default) | `markdown`; selects the renderer
	- `partition_by_domain` — `auto` (if any file has a domain) | `on` | `off`; controls domain-bucketed top-level nodes
	- `views` — per-view emission map (`additionalProperties: false`); each of `file_system`, `keyword`, `tag`, `word`, `dependencies`, `glossary` accepts `auto` | `on` | `off`
- **`types`** — include/exclude built-in handler types (`card`, `markdown`, `freeplane`); `card` is matched by compound suffix `.kb.md` and takes precedence over `markdown`; handlers are built-in — the config only selects which to activate
