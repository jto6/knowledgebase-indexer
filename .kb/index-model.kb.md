---
id: 6f318f4a-4362-44b3-b3e1-75df571ea30f
slug: index-model
title: Render-Independent Index Model
source: ../index_model.py
domain: technical
tags: [kbi, architecture, model, domain-partitioning, knowledgebase]
created: 2026-06-11
updated: 2026-06-11
---

# Render-Independent Index Model

> `index_model.py` defines the central `IndexModel` — a domain-keyed collection of `DomainIndex` objects each holding six named views — plus provenance marking and domain resolution utilities.

## Core Concepts

- **`IndexModel`**: top-level container; `domains` maps domain name (or `None`) → `DomainIndex`; `partitioned` flag signals whether any file had a domain
- **`DomainIndex`**: per-domain bucket holding `files`, `file_system` (non-card files → root nodes), `card_groups` (source → `CardGroup`), `keyword_entries`, `tags`, `words`, `dependencies`, `glossary`, `dir_annotations`
- **`CardGroup`**: groups all cards sharing one source — carries `annotation` (one-line essence for FS view), `hidden_card` (file_summary card suppressed as a leaf), `cards` list `(label, path, essence)`, `exported_as`, `refines`
- **Six view constants**: `VIEW_FILE_SYSTEM`, `VIEW_KEYWORD`, `VIEW_TAG`, `VIEW_WORD`, `VIEW_DEPENDENCIES`, `VIEW_GLOSSARY`; word index defaults **off** (opt-in only via `views.word: on`)
- **Provenance marker** (`KBI_MARKER_TOKEN = "kbi:generated"`): invisible XML/HTML comment stamped into every generated output; `file_is_generated()` scans only the first 4 KB to detect it and short-circuit self-indexing
- **Domain resolution**: card `domain` frontmatter → nearest `kb.yml` `domain` (via `area_domain_for_dir()` walking up the directory tree) → `None`
- **`ordered_domains()`**: real domains alphabetically, `NONE_DOMAIN` last — stable render ordering across runs
- **`view_enabled(config, view, renderer)`**: checks `output.views.<view>` (on/off/auto); word index defaults off; all others default to on-if-data
