---
id: a34a4e10-81a9-48a0-b081-ff5bd56c10f8
slug: keywords
title: Keyword File Processing
source: ../keywords.py
domain: technical
tags: [kbi, keyword-search, configuration, python]
created: 2026-06-11
updated: 2026-06-11
---

# Keyword File Processing

> `keywords.py` parses tab-indented keyword files into a `KeywordEntry` hierarchy where interior nodes are organizational categories and leaf nodes are colon-separated search sequences.

## Core Concepts

- **`KeywordEntry`**: hierarchy node — `text`, `level`, `is_leaf` (True for search patterns, False for category nodes), `children`/`parent`, `line_number`
- **Colon separator**: a leaf entry like `api:reference:guide` becomes the multi-term sequence `["api", "reference", "guide"]` consumed by `HierarchicalSearchEngine`
- **`KeywordFileParser`**: reads lines; computes indentation level from tabs (4 spaces = 1 tab); builds parent-child tree; marks a node `is_leaf=False` when children are added to it
- **`KeywordProcessor`**
	- `extract_all_search_sequences()` — groups sequences by top-level category name; top-level leaves go into a "Direct Searches" bucket
	- `flatten_search_sequences()` — all sequences as a flat list
	- `build_organizational_hierarchy()` — dict tree for display purposes
- **`load_keyword_files()`**: loads and validates multiple files; accumulates root entries and structural warnings (empty entries, colons in non-leaf nodes, nesting ≥ 7 levels)
- **Sample generation**: `create_sample_keyword_file()` writes a commented example file
