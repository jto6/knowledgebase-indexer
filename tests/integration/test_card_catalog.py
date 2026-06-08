#!/usr/bin/env python3
"""
Integration tests for the card catalog pipeline (card-aware indexing → slices).

Exercises the end-to-end path: discover `.kb/*.kb.md` cards, parse them with the
CardHandler (card-only and deep scopes), and render per-domain Markdown slices.
Confirms that `cards.yml` / `kb.yml` and raw sources are ignored, that the slice
carries title/essence/tags/glossary, and that `builds_on` resolves to titles.

The /kb-card segmentation/density logic is prompt-level (not Python) and is
validated by example, not here; this covers the deterministic kbi engine.
"""

import pytest
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kbi import KnowledgebaseIndexer


CARD_A = """---
id: 11111111-1111-1111-1111-111111111111
slug: card-a
title: Card A Title
source: ../thing.md
domain: alpha-domain
tags: [shared-tag, only-a]
defines: [foo-term]
---

# Card A Title

> essence of card A

## Core Concepts

- concept a
"""

CARD_B = """---
id: 22222222-2222-2222-2222-222222222222
slug: card-b
title: Card B Title
source: ../thing.md
domain: alpha-domain
tags: [shared-tag, only-b]
builds_on: [card-a]
---

# Card B Title

> essence of card B

## Core Concepts

- concept b
"""

CARD_C = """---
id: 33333333-3333-3333-3333-333333333333
slug: card-c
title: Card C Title
source: ..
domain: beta-domain
tags: [gamma]
---

# Card C Title

> essence of card C

## Core Concepts

- concept c
"""


def _build_tree(root: Path):
    """Two domains across two leaf dirs, plus noise that must be ignored."""
    a = root / "area1" / ".kb"; a.mkdir(parents=True)
    (a / "thing.caching.kb.md").write_text(CARD_A, encoding="utf-8")
    (a / "thing.queue.kb.md").write_text(CARD_B, encoding="utf-8")
    # noise that must NOT be treated as cards:
    (a / "cards.yml").write_text("version: 1\ncards: []\n", encoding="utf-8")
    (a / "kb.yml").write_text("domain: alpha-domain\n", encoding="utf-8")
    (root / "area1" / "thing.md").write_text("# Raw source\n\nNot a card.\n", encoding="utf-8")

    b = root / "area2" / ".kb"; b.mkdir(parents=True)
    (b / "doc.kb.md").write_text(CARD_C, encoding="utf-8")


def _card_only_config(root: Path, out: Path):
    return {
        "directories": {"include": [str(root)], "exclude": []},
        "keywords": {"files": []},
        "output": {"file": str(out), "format": "markdown"},
        "file_types": {"card": {"extensions": [".kb.md"], "handler": "CardHandler"}},
    }


@pytest.mark.integration
class TestCardCatalogPipeline:
    def test_card_only_scope_renders_per_domain_slices(self, temp_dir):
        _build_tree(temp_dir)
        out = temp_dir / "catalog"
        generator = KnowledgebaseIndexer(_card_only_config(temp_dir, out))
        result = generator.run()

        assert result == str(out)
        # one slice per domain + the overview
        assert {p.name for p in out.iterdir()} == {"alpha-domain.md", "beta-domain.md", "INDEX.md"}

        alpha = (out / "alpha-domain.md").read_text()
        # card titles + essences present
        assert "- Card A Title" in alpha
        assert "essence of card A" in alpha
        # tag clustering: shared-tag groups both cards
        cluster = alpha.split("- shared-tag", 1)[1].split("##", 1)[0]
        assert "Card A Title" in cluster and "Card B Title" in cluster
        # builds_on resolved to the referenced card's title
        assert "builds on: Card A Title" in alpha
        # glossary maps the defined term to its card
        assert "foo-term — Card A Title" in alpha

        index = (out / "INDEX.md").read_text()
        assert "alpha-domain](alpha-domain.md) — 2 card(s)" in index
        assert "beta-domain](beta-domain.md) — 1 card(s)" in index

    def test_cards_yml_kbyml_and_raw_sources_are_ignored(self, temp_dir):
        _build_tree(temp_dir)
        out = temp_dir / "catalog"
        generator = KnowledgebaseIndexer(_card_only_config(temp_dir, out))
        files = generator.discover_files()
        # exactly the three .kb.md cards — never cards.yml, kb.yml, or thing.md
        assert len(files) == 3
        assert all(f.endswith(".kb.md") for f in files)

    def test_deep_scope_still_parses_cards_card_aware(self, temp_dir):
        """With markdown + card types enabled, a .kb.md is still handled by the
        CardHandler (precedence), so slices render identically."""
        _build_tree(temp_dir)
        out = temp_dir / "catalog"
        config = _card_only_config(temp_dir, out)
        config["file_types"]["markdown"] = {"extensions": [".md", ".markdown"],
                                             "handler": "MarkdownHandler"}
        generator = KnowledgebaseIndexer(config)
        generator.run()
        alpha = (out / "alpha-domain.md").read_text()
        # title-labeled (CardHandler), not filename — proves precedence held
        assert "- Card A Title" in alpha
        assert "foo-term — Card A Title" in alpha
