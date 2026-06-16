---
id: ec83a881-b248-4a38-8c35-48de15f8ee69
slug: mindmap-generator
title: Freeplane Mindmap Generator
source: "[mindmap_generator.py](<../mindmap_generator.py>)"
domain: technical
tags: [kbi, rendering, freeplane, architecture, model]
created: 2026-06-11
updated: 2026-06-16
---

# Freeplane Mindmap Generator

> `mindmap_generator.py` serializes the index model to a Freeplane-compatible `.mm` XML file, rendering all six views as hierarchical branches under a root "Navigation Index" node.

## Core Concepts

- **`FreeplaneMapGenerator`**: owns `output_path`, `used_ids` (collision-free IDs), `_card_essence_map` (card_path → essence), and `_card_source_map` (card_path → source_path); primary entry point is `render_model()`
- **`render_model()`**: D16-compliant entry point; with multiple domains, renders global merged views at top level plus per-domain drill-down under a "Domains" branch via `_merge_domain_indexes()`; single domain gets a "Domain: X" wrapper
- **`_render_domain_views()`**: builds `_card_essence_map` and `_card_source_map` from `card_groups`, then renders each enabled non-empty view (FS, keyword, tag, word, dependencies, glossary)
- **`_merge_domain_indexes()` + `_merge_keyword_entries()`**: build a synthetic `DomainIndex` by merging all domains' views; keyword entries are deduplicated by `.text`, with search results and children merged
- **File System view** (`_create_file_system_index`): directory hierarchy with `LINK` attributes; card groups shown under their source node with optional essence DETAILS annotation; directory nodes annotated from `dir_annotations`
- **`_add_details(node, text)`**: attaches a collapsed DETAILS panel (`richcontent TYPE=DETAILS HIDDEN=true`) carrying the essence text
- **`_add_card_source_link(card_node, card_path)`**: appends a sole child to a `.kb.md` file node linking back to its source file (via `_card_source_map`); used in keyword, tag, and word views
- **`_display_path(file_path)`**: strips the home directory prefix, then replaces `/.kb/` with `::` — so `dev/proj/.kb/card.kb.md` renders as `dev/proj::card.kb.md`
- **Letter-bucket grouping**: `_group_children_by_letter(parent, threshold=20)` re-parents children into per-letter (A–Z, `#`) buckets when count exceeds threshold; oversized buckets are further split by `_group_children_by_range()` into equal-size chunks labeled with prefix-range strings (`"SAF–SMO"`); applied to keyword and tag index roots
- **`_linked_node()`**: creates a `<node>` with `TEXT` + optional `LINK` (relative path preferred; falls back to absolute)
- **Markdown anchors**: `_generate_markdown_anchor()` converts heading text to GitHub-style `#anchor`; `_find_markdown_heading_node()` traverses up to the nearest heading ancestor
- **XML formatting**: `minidom.parseString()` / `toprettyxml()` with post-processing to strip blank lines; provenance marker comment inserted inside `<map>` to mark the output as kbi-generated
- **Legacy `create_mind_map()`**: older entry point taking pre-built view dicts directly
