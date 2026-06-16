---
id: 489b8533-e603-487a-9759-def8ad1abcce
slug: kb-rename-domain
title: KB Rename Domain Utility
source: ../kb-rename-domain.py
domain: technical
tags: [kbi, utility, cli, knowledgebase, python]
created: 2026-06-11
updated: 2026-06-11
---

# KB Rename Domain Utility

> `kb-rename-domain.py` is a CLI utility that renames the `domain:` field across `.kb.md` card frontmatter and `kb.yml` config files, with optional recursion and dry-run preview.

## Core Concepts

- **Scope flexibility**: accepts a single `.kb.md` file, a `.kb` directory, or any parent directory; `-r` recurses into all nested `.kb` directories under the given root
- **Targeted replacement**
	- `_update_card_file()`: operates only within the YAML frontmatter block (between the first pair of `---` delimiters) to avoid false matches in card body text
	- `_update_kb_yml()`: replaces `domain: <old>` in `kb.yml` files
- **`collect_files()`**: handles the three scope cases (file / `.kb` dir / parent dir) and yields eligible `.kb.md` and `kb.yml` files
- **Dry run** (`-n`/`--dry-run`): shows "would update: <path>" without writing; reports changed/unchanged counts either way
- **Typical use**: after renaming a domain value, run `kb-rename-domain.py -r <repo-root> old-domain new-domain` to update all cards and configs in one pass
