---
id: 7b7289d6-e382-4aaa-a8ea-f9e1598a6a2c
slug: readme
title: Knowledgebase Indexer — Overview
source: ../README.md
domain: technical
tags: [kbi, indexer, knowledgebase, architecture, freeplane, markdown, configuration]
created: 2026-06-11
updated: 2026-06-11
---

# Knowledgebase Indexer — Overview

> kbi is a Python tool that scans structured file collections (`.mm`, `.md`, `.kb.md`), builds a render-independent four-view index model, and emits it as Freeplane mindmaps or Markdown navigational indexes.

## Core Concepts

- **Four navigation views**
	- File System — directory hierarchy mirroring physical structure
	- Keyword — context-sensitive search results driven by a keyword file
	- Tag — files grouped by extracted tags
	- Word — significant-word frequency index (opt-in)
- **Render-independent model**: views are computed once; the Freeplane `.mm` and Markdown renderers serialize the same model (adding a new renderer doesn't touch the engine)
- **Pluggable file handlers**: Freeplane `.mm`, Markdown `.md`, distilled card `.kb.md` — selected by longest-extension precedence so `.kb.md` is always handled as a card, not plain markdown
- **Configurable file discovery**: YAML config selects directories, include/exclude glob patterns, keyword files, output format, and which views to emit
- **Card integration**: `.kb.md` cards are indexed card-aware — tags and title come from YAML frontmatter, not the filename or body hashtags
- **Domain partitioning**: files are routed to domain buckets via nearest `kb.yml`; partitioned indexes split all views per domain
- **Self-indexing prevention**: every generated output carries an invisible provenance comment so re-runs skip their own prior output
- **CLI flags**: `--config`, `--output`, `--debug`, `--sample-config`, `--sample-keywords`, `--update`
