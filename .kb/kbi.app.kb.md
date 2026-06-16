---
id: 9f5be35a-24ad-44b6-bdd2-50c043cae9fd
slug: kbi-app
title: KBI Main Application
source: "[kbi.py](<../kbi.py>)"
domain: technical
tags: [kbi, indexer, architecture, python, file-discovery, model]
created: 2026-06-11
updated: 2026-06-16
---

# KBI Main Application

> `kbi.py` is the main orchestrator — it wires together file discovery, handler dispatch, index model construction (FS/keyword/tag/word/deps/glossary views), and rendering, all driven by `KnowledgebaseIndexer`.

## Core Concepts

- **`KnowledgebaseIndexer`**: top-level class; `__init__` registers built-in handlers and assembles the component graph (config, search engine, keyword processor)
- **`BUILTIN_TYPES`**: the three built-in types: `card` (`.kb.md`), `freeplane` (`.mm`), `markdown` (`.md`/`.markdown`); type selection by `types:` config block (include/exclude or all)
- **`_DEFAULT_SOURCE_EXCLUDE`**: module-level list of built-in source-exclude glob patterns used by the staleness scanner — `*.conflict*` (sync-conflict artefacts), `*.mm.md` (derived mm2md outputs), `CLAUDE.md` (Claude Code project instructions); always applied even without a `kb.yml`; users extend (not replace) via `kb.yml source_exclude`
- **File type dispatch**: `_type_of(filename)` picks the longest-extension match — `.kb.md` is classified as `card`, never `markdown`
- **`discover_files()`**: `os.walk` with **in-place directory pruning** (`dirnames.remove()`) for excluded patterns — avoids descending into large trees; skips generated outputs via `file_is_generated()`; skips the configured output file path
- **Model construction pipeline**
	- `build_file_system_index()` — non-card files → root nodes; excludes `exported_as` and `refines` paths
	- `build_card_groups()` — card files → `CardGroup` per source path (annotation, hidden_card, cards list, exported_as, refines)
	- `build_dir_annotations()` — extracts `kind: dir_summary` card essences into an `abs_dir → essence` map
	- keyword search, tag extraction, word extraction, dependency/glossary collection
	- Domain routing via `resolve_domain()` → `IndexModel` / `DomainIndex`
- **Card source resolution**: `_resolve_card_source()` handles string, list (URL + local), or pure-URL sources; strips markdown link syntax `[text](<path>)` via `_parse_md_link_path()` before resolving; URL-only cards have no local FS source
- **`_resolve_path_list(card_record, field)`**: shared helper for `exported_as` and `refines` — resolves relative paths to absolute, drops URL entries
- **`_resolve_keyword_files(domain)`**: returns keyword file paths applicable to the current domain; plain strings are global; `{path, domain}` dicts are domain-scoped (domain may be a string or list); `NONE_DOMAIN` gets only global files
- **`_split_keyword_sequence(text)`** (static): bracket-depth-aware `:` splitter — only splits on `:` outside `[...]` character classes, so patterns like `1[-:]1s?` are not torn mid-class; used by `_execute_keyword_searches()`, which also wraps each entry's search in a `try/except` to isolate malformed patterns (skipped with debug warning) rather than aborting the entire keyword index
- **`--update` mode** (two-level staleness check):
	- `_scan_managed_directories(config)` — walks include dirs, returns `(stale_dirs, current_count)`; for each `.kb/segmentation.yml`:
		1. mtime-based `dir_fingerprint` (fast) — if unchanged, skip immediately
		2. content-based `_dir_content_changed(seg, kb_dir)` — if `dir_fingerprint` changed but all `source_hash` values still match and no uncarded source files exist, skip Claude (avoids false positives from mtime-only changes like `git checkout` or sync)
	- `_dir_content_changed()` — checks stored `source_hash` per card against fresh SHA-256 of each source file; also scans the directory for new files not yet in any card (filtered by `_load_source_exclude`); returns True if any file added/removed/changed/uncarded
	- `_load_source_exclude(source_dir)` — returns `_DEFAULT_SOURCE_EXCLUDE` + any `source_exclude` patterns from the nearest ancestor `kb.yml`
	- `run_update()` — calls `_scan_managed_directories()`; prints progress (stale list, total/stale/current summary); invokes `claude -p /kb-card` with `cwd=d` (not as a CLI arg) for each stale directory; progress output uses `flush=True`
- **Renderers**: `FreeplaneMapGenerator.render_model()` or `MarkdownIndexRenderer.render_model()` consume the same `IndexModel`; format selected by `output.format` config
