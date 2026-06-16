---
id: 01baa6c5-6346-410b-954a-a0c8585c3ada
slug: core-handlers
title: Core Handlers and Base Classes
source: ../core_handlers.py
domain: technical
tags: [kbi, architecture, handler, python, search]
created: 2026-06-11
updated: 2026-06-11
---

# Core Handlers and Base Classes

> `core_handlers.py` defines the shared `HierarchicalNode` data structure, the abstract `FileHandler` interface, and the `HandlerRegistry` that assigns handlers by longest-extension precedence.

## Core Concepts

- **`HierarchicalNode`**: the universal tree node used by all handlers and the search engine — fields: `id`, `content`/`text`, `file_path`, `parent`/`children` list, `node_type`, `metadata`
- **`FileHandler` (ABC)**: contract for all file type plugins — `can_handle()`, `get_root_nodes()`, `get_child_nodes()`, `get_node_content()`; also provides `extract_tags()`, `generate_link()`, `search_in_node_subtree()`
- **`HandlerRegistry`**: maps handler class names → class instances; `get_handler_for_file()` finds the best match by **longest extension** — so `.kb.md` outranks `.md` regardless of registration order
- **Regex helpers**
	- `create_word_boundary_pattern(keyword)` — escapes literal keyword, attaches adaptive `\b` boundaries
	- `create_word_boundary_regex_pattern(pattern)` — treats input as raw regex, wraps with `\b(?:…)\b`
	- `create_regex_pattern(pattern)` — raw regex, no boundaries
- **ID helpers**: `generate_unique_id()` (timestamp + random, Freeplane format), `get_current_timestamp()` (`YYYYMMDDTHHMMSS`)
- **Global registry**: `handler_registry` singleton imported by `kbi.py` for all dispatch
