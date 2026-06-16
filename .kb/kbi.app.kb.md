---
id: 9f5be35a-24ad-44b6-bdd2-50c043cae9fd
slug: kbi-app
title: KBI Main Application
source: ../kbi.py
domain: technical
tags: [kbi, indexer, architecture, python, file-discovery, model]
created: 2026-06-11
updated: 2026-06-11
---

# KBI Main Application

> `kbi.py` is the main orchestrator — it wires together file discovery, handler dispatch, index model construction (FS/keyword/tag/word/deps/glossary views), and rendering, all driven by `KnowledgebaseIndexer`.

## Core Concepts

- **`KnowledgebaseIndexer`**: top-level class; `__init__` registers built-in handlers and assembles the component graph (config, search engine, keyword processor)
- **`BUILTIN_TYPES`**: the three built-in types: `card` (`.kb.md`), `freeplane` (`.mm`), `markdown` (`.md`/`.markdown`); type selection by `types:` config block (include/exclude or all)
- **File type dispatch**: `_type_of(filename)` picks the longest-extension match — `.kb.md` is classified as `card`, never `markdown`
- **`discover_files()`**: `os.walk` with **in-place directory pruning** (`dirnames.remove()`) for excluded patterns — avoids descending into large trees; skips generated outputs via `file_is_generated()`; skips the configured output file path
- **Model construction pipeline**
	- `build_file_system_index()` — non-card files → root nodes; excludes `exported_as` derivatives
	- `build_card_groups()` — card files → `CardGroup` per source path (annotation, hidden_card, cards list, exported_as, refines)
	- keyword search, tag extraction, word extraction, dependency/glossary collection
	- Domain routing via `resolve_domain()` → `IndexModel` / `DomainIndex`
- **Card source resolution**: `_resolve_card_source()` handles string, list (URL + local), or pure-URL sources; URL-only cards have no local FS source
- **`--update` mode**: compares `source_hash` from `segmentation.yml` against current file hashes; rebuilds only changed card-source pairs
- **Renderers**: `FreeplaneMapGenerator.render_model()` or `MarkdownIndexRenderer.render_model()` consume the same `IndexModel`; format selected by `output.format` config
