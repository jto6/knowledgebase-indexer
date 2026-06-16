---
id: f6c9d6bd-692f-4bc6-ac71-4eabc976b5ae
slug: kbi-init
title: KBI Package Init (Lazy Import)
source: ../__init__.py
domain: technical
tags: [kbi, package, lazy-import, testing, python]
created: 2026-06-11
updated: 2026-06-11
---

# KBI Package Init (Lazy Import)

> Enables `from kbi import KnowledgebaseIndexer` in test contexts by lazy-loading `kbi.py` under a private module alias, resolving the standalone-script / importable-package tension without circular imports.

## Core Concepts

- **Problem it solves**: `kbi.py` is a standalone script; making it importable as a package for tests requires loading it under an alias that doesn't clash with the `kbi` package itself
- **Lazy-load mechanism**: `_load_kbi_main()` uses `importlib.util.spec_from_file_location` to load `kbi.py` as `_kbi_main_module`, caching in `sys.modules` to prevent double-execution
- **`__getattr__` passthrough**: any attribute in `__all__` is forwarded to the loaded module on first access — zero-cost unless the attribute is actually imported
- **Exported symbols**: `__all__ = ['KnowledgebaseIndexer', 'run_search']` — the public test-facing surface
