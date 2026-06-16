---
id: 4df0ddb1-7af7-4de5-aca5-91ba0ab06979
slug: kbi-dir
title: KBI Root Directory
kind: dir_summary
source: ..
domain: technical
tags: [kbi, indexer, knowledgebase, architecture, python, testing]
created: 2026-06-11
updated: 2026-06-16
---

# KBI Root Directory

> The kbi root module implements the Knowledgebase Indexer — a Python tool that scans structured file collections, builds a render-independent six-view navigational index, and emits it as Freeplane mindmaps or Markdown, with a layered testing infrastructure.

## Core Concepts

- **Orchestrator** (`kbi.py`): file discovery with directory pruning, handler dispatch by longest-extension, `IndexModel` construction, renderer selection; `--update` mode uses a two-level staleness check (mtime `dir_fingerprint` → content `source_hash`/new-file scan) to avoid false positives from `git checkout` and sync, then invokes `claude -p /kb-card` with `cwd=<dir>` per genuinely stale directory; `_DEFAULT_SOURCE_EXCLUDE` and `kb.yml source_exclude` filter sync-conflict artefacts and derived outputs from the staleness signal; self-indexing prevention via provenance marker
- **Render-independent model** (`index_model.py`): `IndexModel` / `DomainIndex` with six named views (FS, keyword, tag, word, dependencies, glossary); `CardGroup` tracks all cards for a source; domain partitioning routes files to named buckets
- **Handler layer** (`core_handlers.py`): `HierarchicalNode` universal tree node; `FileHandler` ABC; `HandlerRegistry` with longest-extension precedence; handlers in `handlers/` for Freeplane, Markdown, and cards
- **Search and keywords** (`search.py`, `keywords.py`): `HierarchicalSearchEngine` narrows scope through colon-separated keyword sequences (`:` inside character classes is not split); `KeywordFileParser` parses tab-indented keyword files where leaf nodes are search patterns; domain-scoped keyword files via `{path, domain}` dict entries
- **Renderers**: `mindmap_generator.py` (Freeplane XML with letter-bucket grouping, essence DETAILS panels, source-link children for card nodes, and global cross-domain merge views) and `markdown_renderer.py` (Markdown navigational index) both serialize the same model as linked hierarchies
- **Configuration layer**: `config.py` (YAML loading, JSON Schema validation against `config_schema.json`), `config_schema.json` (draft-07 contract — enforces `directories`, `keywords.files` with global and domain-scoped forms, `output`, `views`, `types`)
- **Supporting modules**: `word_filter.py` (technical stop-word extraction), `logging_config.py` (dual-sink logging + `LoggedOperation`), `kb-rename-domain.py` (domain rename CLI utility)
- **Package and test infrastructure**: `__init__.py` (lazy import of `KnowledgebaseIndexer` / `run_search` for test imports), `run_tests.py` (pytest CLI wrapper with five suites: quick, unit, integration, all, coverage)
