---
id: 9f5be35a-24ad-44b6-bdd2-50c043cae9fd
slug: kbi-app
title: KBI Main Application
source: "[kbi.py](<../kbi.py>)"
domain: technical
tags: [kbi, indexer, architecture, python, file-discovery, model, update-mode, decisions]
created: 2026-06-11
updated: 2026-07-18
---

# KBI Main Application

> `kbi.py` is the main orchestrator — it wires together file discovery, handler dispatch, index model construction (FS/keyword/tag/word/deps/glossary views), rendering, and a token-efficient `--update` pipeline (staleness → delta → `/kb-card` handoff → auto-commit → audit trail), all driven by `KnowledgebaseIndexer`.

## Core Concepts

- **`KnowledgebaseIndexer`**: top-level class; `__init__` registers built-in handlers and assembles the component graph (config, search engine, keyword processor)
- **`BUILTIN_TYPES`**: the three built-in types: `card` (`.kb.md`), `freeplane` (`.mm`), `markdown` (`.md`/`.markdown`); type selection by `types:` config block (include/exclude or all)
- **`_DEFAULT_SOURCE_EXCLUDE`**: module-level list of built-in source-exclude glob patterns used by the staleness scanner — `*.conflict*` (sync-conflict artefacts), `*.mm.md` (derived mm2md outputs), `CLAUDE.md` (Claude Code project instructions); always applied even without a `kb.yml`; users extend (not replace) via `kb.yml source_exclude`
- **File type dispatch**: `_type_of(filename)` picks the longest-extension match — `.kb.md` is classified as `card`, never `markdown`
- **`discover_files()`**: `os.walk` with **in-place directory pruning** (`dirnames.remove()`) for excluded patterns — avoids descending into large trees; skips generated outputs via `file_is_generated()`; skips the configured output file path
- **Model construction pipeline**
	- `build_file_system_index()` — non-card files → root nodes; excludes `exported_as` and `refines` paths
	- `build_card_groups()` — card files → `CardGroup` per source path (annotation, hidden_card, cards list, exported_as, refines)
	- `build_dir_annotations()` — extracts `kind: dir_summary` card essences into an `abs_dir → essence` map
	- keyword search, tag extraction, word extraction, dependency/glossary collection
	- Domain routing via `resolve_domain()` → `IndexModel` / `DomainIndex`
- **Card source resolution**: `_resolve_card_source()` handles string, list (URL + local), or pure-URL sources; strips markdown link syntax `[text](<path>)` via `_parse_md_link_path()` before resolving; URL-only cards have no local FS source
- **`_resolve_path_list(card_record, field)`**: shared helper for `exported_as` and `refines` — resolves relative paths to absolute, drops URL entries
- **`_resolve_keyword_files(domain)`**: returns keyword file paths applicable to the current domain; plain strings are global; `{path, domain}` dicts are domain-scoped (domain may be a string or list); `NONE_DOMAIN` gets only global files
- **`_split_keyword_sequence(text)`** (static): bracket-depth-aware `:` splitter — only splits on `:` outside `[...]` character classes, so patterns like `1[-:]1s?` are not torn mid-class; used by `_execute_keyword_searches()`, which also wraps each entry's search in a `try/except` to isolate malformed patterns (skipped with debug warning) rather than aborting the entire keyword index
- **`--update` mode** (two-level staleness check, then a per-directory content delta handed to `/kb-card`):
	- `_scan_managed_directories(config)` — walks include dirs, returns `(stale_dirs, current_count)` where `stale_dirs` is `[(abs_path, delta)]`; for each `.kb/segmentation.yml`:
		1. mtime-based `dir_fingerprint` (fast) — if unchanged, skip immediately
		2. content-based `_dir_content_delta(seg, kb_dir)` / `_delta_has_drift()` — if `dir_fingerprint` changed but the computed delta shows no real drift, skip Claude (avoids false positives from mtime-only changes like `git checkout` or sync); otherwise the delta is kept for the `/kb-card --delta` handoff
	- `_dir_content_delta(seg, kb_dir)` — the authoritative delta computation, returning `{bootstrap, changed, new, deleted, reopened, pending, unchanged}`:
		- `changed` — tracked sources whose bytes no longer match their recorded `source_hash` (`{path, old_hash, new_hash, cards}`)
		- `new` — untracked files with a tracked extension, filtered by `_load_source_exclude` and not already absorbed/excluded
		- `deleted` — tracked sources gone from disk
		- `reopened` — absorbed (`supersedes`/`exported_as`/`refines`) or `excluded` entries whose recorded hash drifted — the decision needs re-deciding
		- `pending` — card entries checkpointed with `status: pending` (plan written, body not yet authored) — an interrupted run to resume
		- files behind a hashed `supersedes`/`exported_as`/`refines`/`excluded` entry that still matches are settled and never resurface as `new`
	- `_load_source_exclude(source_dir)` — returns `_DEFAULT_SOURCE_EXCLUDE` + any `source_exclude` patterns from the nearest ancestor `kb.yml`
	- `_write_delta_file(root, directory, delta)` — serializes the delta to `/tmp/kbi-update/<slug>-<hash8>.delta.yml`; for each `changed` entry, attaches a best-effort unified `diff` via `_source_diff()` when recoverable
	- `_source_diff(directory, rel_path, old_hash)` — recovers the previous version from `git show HEAD:./<rel_path>` (only trustworthy right after a `--update` auto-commit, verified by re-hashing); `.mm` sources are converted through `_mm_pair_to_md()` (uses the same `mm2md.py` converter as `/kb-card`) before diffing; returns `None` (agent reads the source itself) for binary content, an unrecoverable old version, or a diff over `_DIFF_MAX_LINES` (200) lines
	- `run_update()` — calls `_scan_managed_directories()`; prints progress (stale list, total/stale/current summary); for each stale directory writes its delta file and invokes `claude -p '/kb-card --delta <file>'` (falls back to plain `/kb-card` if the delta file couldn't be written) with `cwd=d`; on success calls `_commit_kb_updates()` (unless `--no-commit`); aborts the remaining loop on a spend/usage-limit signal (`_is_budget_exhausted()`) or two consecutive failures, leaving the rest stale for the next run
	- `_commit_kb_updates(directory, body)` — auto-commits only `.kb/` paths (`git commit --only -s -- .kb`) when the directory is a git work tree, `update_commit` (nearest `kb.yml`, default `True`) allows it, and `.kb/` is dirty; the commit body is `_extract_decisions(proc.stdout)` — the report's "Decisions made" section — so headless judgment calls land in `git log` as a durable decision journal
- **Decision audit trail**: every `excluded`/`supersedes`/`exported_as` manifest entry carries `decided: user|auto` + `decided_on`; `run_decisions(argv)` (`kbi decisions [<root>]`) walks a tree for managed directories and prints all `decided: auto` entries newest-first (or `--all` to include `decided: user` too) — the audit surface for judgment calls `/kb-card --delta` made unattended
- **Mechanical manifest helpers** (own the hash/manifest bookkeeping so `/kb-card` never hand-computes them):
	- `run_hash(argv)` (`kbi hash <file>...`) — prints `sha256:<hex>  <path>` per file, the canonical `source_hash`
	- `run_manifest_sync(argv)` (`kbi manifest-sync [<dir>]`) — recomputes every card's `source_hash`, hashed `supersedes`/`exported_as`/`refines`/`excluded` entries, `dir_hash` on `dir_summary` cards, `dir_fingerprint`, and `updated`; ratifies current on-disk bytes as decided state — run as the last step of a successful `/kb-card` pass, never to silence unreviewed drift
	- `_compute_dir_hash(source_hashes)` — canonical `dir_hash` formula: sha256 of the sorted, deduplicated `source_hash` values, newline-joined
	- `run_search(argv)` (`kbi search <config> "<regex>"`) — discovers exactly the files a config covers, then shells out to ripgrep (else grep) over that set, chunked to stay under `ARG_MAX`
- **`main()` dispatch**: `search`/`hash`/`manifest-sync`/`decisions` as `argv[0]` route to their `run_*` function before the main argparse parser runs; otherwise the normal config-driven index-generation path (with `--update`/`--no-commit`) applies
- **Renderers**: `FreeplaneMapGenerator.render_model()` or `MarkdownIndexRenderer.render_model()` consume the same `IndexModel`; format selected by `output.format` config
