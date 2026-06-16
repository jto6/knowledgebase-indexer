---
id: 793eea75-f12b-4230-9351-5cd91f9f660e
slug: markdown-renderer
title: Markdown Index Renderer
source: ../markdown_renderer.py
domain: technical
tags: [kbi, rendering, markdown, architecture, model]
created: 2026-06-11
updated: 2026-06-11
---

# Markdown Index Renderer

> `markdown_renderer.py` serializes the index model as a navigational Markdown index — links to file locations, never content — writing `INDEX.md` plus per-domain files when the model is partitioned.

## Core Concepts

- **`MarkdownIndexRenderer`**: renders to a directory (creates if needed); writes `INDEX.md` and optionally per-domain `<slug>.md` files
- **Navigational, not content**: every view is a nested-list of `[label](<path>)` links; the renderer never includes indexed file content
- **Partitioned output**: when `model.partitioned`, `INDEX.md` lists domains with file counts; each domain gets its own `<domain>.md` with all six views
- **File System view**: builds a path tree using `os.path.commonpath` as base; card groups shown as source node (with inline essence) + indented topic-card children; directory nodes annotated with `dir_annotations` essence
- **Provenance header**: every file opens with the kbi marker comment and a "do not edit" preamble
- **`_slugify()`**: lowercase, non-alnum replaced with `-`, for domain file names
- **Six views**: same as Freeplane — FS, keyword, tag, word, dependencies, glossary; `view_enabled()` gates each one; word index off by default
- **Card label resolution**: `.kb.md` files use their H1 title as label; all other files use the filename
