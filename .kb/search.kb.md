---
id: 6ff64ea4-cd56-450f-bc02-ebb12e04d116
slug: search
title: Hierarchical Search Engine
source: ../search.py
domain: technical
tags: [kbi, search, keyword-search, python, architecture]
created: 2026-06-11
updated: 2026-06-11
---

# Hierarchical Search Engine

> `search.py` implements `HierarchicalSearchEngine`, which narrows candidates through a colon-separated keyword sequence — each successive keyword restricts the search scope to the subtrees of the previous keyword's matches.

## Core Concepts

- **`HierarchicalSearchEngine`**
	- First keyword: searches entire file trees (all root nodes, full subtrees)
	- Subsequent keywords: each one restricts to the subtrees of prior matches, progressively narrowing scope
	- Last keyword in the sequence: `include_descendants=True` so all leaf matches within the subtree are collected
- **`SearchResult`**: captures `file_path`, matched `HierarchicalNode`, `matched_content`, and the `search_path` list recording which keywords led here
- **`search_multiple_sequences()`**: runs all sequences from a keyword file and returns results keyed by `"k1:k2:…"` string
- **`SearchResultAggregator`**: utility methods — `flatten_results()`, `sort_results()` (by file/node/path), `deduplicate_results()`, `filter_by_file_type()`
- **Pattern delegation**: all patterns are built via `core_handlers.create_word_boundary_regex_pattern` — raw regex with `\b(?:…)\b` word-boundary wrapping, case-insensitive
- **`search_files()` convenience**: parses a colon-separated string into a sequence and delegates to the engine
