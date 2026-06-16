---
id: ec83a881-b248-4a38-8c35-48de15f8ee69
slug: mindmap-generator
title: Freeplane Mindmap Generator
source: ../mindmap_generator.py
domain: technical
tags: [kbi, rendering, freeplane, architecture, model]
created: 2026-06-11
updated: 2026-06-11
---

# Freeplane Mindmap Generator

> `mindmap_generator.py` serializes the index model to a Freeplane-compatible `.mm` XML file, rendering all six views as hierarchical branches under a root "Navigation Index" node.

## Core Concepts

- **`FreeplaneMapGenerator`**: owns the output path and a `used_ids` set for collision-free node IDs; primary entry point is `render_model()`
- **`render_model()`**: the current D16-compliant entry point; when `model.partitioned`, partitions the top level with "Domain: X" nodes; calls `_render_domain_views()` for each domain
- **`_render_domain_views()`**: renders FS, keyword, tag, word, dependencies, glossary — only non-empty, non-suppressed views (via `view_enabled()`)
- **File System view** (`_create_file_system_index`): directory hierarchy with `LINK` attributes; card groups shown under their source node with optional essence annotation; dir nodes annotated from `dir_annotations`
- **`_linked_node()`**: creates a `<node>` with `TEXT` + optional `LINK` (relative path preferred; falls back to absolute)
- **Markdown anchors**: `_generate_markdown_anchor()` converts heading text to GitHub-style `#anchor` for deep-linking into `.md` files; traverses up to nearest heading ancestor for non-heading nodes
- **XML formatting**: `minidom.parseString()` / `toprettyxml()` with post-processing to remove spurious blank lines
- **Legacy `create_mind_map()`**: older entry point that takes pre-built view dicts directly; still present for compatibility
