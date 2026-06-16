---
id: 4df0ddb1-7af7-4de5-aca5-91ba0ab06979
slug: kbi-dir
title: KBI Root Directory
kind: dir_summary
source: ..
domain: technical
tags: [kbi, indexer, knowledgebase, architecture, python, testing]
created: 2026-06-11
updated: 2026-06-11
---

# KBI Root Directory

> The kbi root module implements the Knowledgebase Indexer — a Python tool that scans structured file collections, builds a render-independent six-view navigational index, and emits it as Freeplane mindmaps or Markdown, with a layered testing infrastructure.

## Core Concepts

- **Orchestrator** (`kbi.py`): file discovery with directory pruning, handler dispatch by longest-extension, `IndexModel` construction, renderer selection; self-indexing prevention via provenance marker
- **Render-independent model** (`index_model.py`): `IndexModel` / `DomainIndex` with six named views (FS, keyword, tag, word, dependencies, glossary); `CardGroup` tracks all cards for a source; domain partitioning routes files to named buckets
- **Handler layer** (`core_handlers.py`): `HierarchicalNode` universal tree node; `FileHandler` ABC; `HandlerRegistry` with longest-extension precedence; handlers in `handlers/` for Freeplane, Markdown, and cards
- **Search and keywords** (`search.py`, `keywords.py`): `HierarchicalSearchEngine` narrows scope through colon-separated keyword sequences; `KeywordFileParser` parses tab-indented keyword files where leaf nodes are search patterns
- **Renderers**: `mindmap_generator.py` (Freeplane XML) and `markdown_renderer.py` (Markdown navigational index) both serialize the same model as linked hierarchies
- **Configuration layer**: `config.py` (YAML loading, JSON Schema validation against `config_schema.json`), `config_schema.json` (draft-07 contract — enforces `directories`, `keywords`, `output`, `views`, `types`)
- **Supporting modules**: `word_filter.py` (technical stop-word extraction), `logging_config.py` (dual-sink logging + `LoggedOperation`), `kb-rename-domain.py` (domain rename CLI utility)
- **Package and test infrastructure**: `__init__.py` (lazy import of `KnowledgebaseIndexer` / `run_search` for test imports), `run_tests.py` (pytest CLI wrapper with five suites: quick, unit, integration, all, coverage)
