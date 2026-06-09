#!/usr/bin/env python3
"""
Integration tests for the unified index model and its renderers (D16).

Covers the pure key→location index: domain partitioning, the markdown renderer's
per-domain files + INDEX overview, the file-system / tags / dependencies /
glossary views (links, no content duplication), the word-index default + override,
per-view suppression, the no-domain single-INDEX case, and the Freeplane domain/
card-view branches.
"""

import pytest
from pathlib import Path
import xml.etree.ElementTree as ET

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
"""


def _build_cards(root: Path):
    a = root / "area1" / ".kb"; a.mkdir(parents=True)
    (a / "thing.caching.kb.md").write_text(CARD_A, encoding="utf-8")
    (a / "thing.queue.kb.md").write_text(CARD_B, encoding="utf-8")
    (a / "cards.yml").write_text("version: 1\ncards: []\n", encoding="utf-8")
    (a / "kb.yml").write_text("domain: alpha-domain\n", encoding="utf-8")
    (root / "area1" / "thing.md").write_text("# Raw\n\nNot a card.\n", encoding="utf-8")
    b = root / "area2" / ".kb"; b.mkdir(parents=True)
    (b / "doc.kb.md").write_text(CARD_C, encoding="utf-8")


def _md_config(root: Path, out: Path, views=None):
    cfg = {
        "directories": {"include": [str(root)], "exclude": []},
        "keywords": {"files": []},
        "output": {"file": str(out), "format": "markdown"},
        "types": {"include": ["card"]},
    }
    if views is not None:
        cfg["output"]["views"] = views
    return cfg


@pytest.mark.integration
class TestMarkdownIndex:
    def test_partitions_by_domain_with_overview(self, temp_dir):
        _build_cards(temp_dir)
        out = temp_dir / "catalog"
        KnowledgebaseIndexer(_md_config(temp_dir, out)).run()
        assert {p.name for p in out.iterdir()} == {"INDEX.md", "alpha-domain.md", "beta-domain.md"}
        index = (out / "INDEX.md").read_text()
        assert "[alpha-domain](alpha-domain.md) — 2 file(s)" in index
        assert "[beta-domain](beta-domain.md) — 1 file(s)" in index

    def test_pure_index_links_no_content(self, temp_dir):
        _build_cards(temp_dir)
        out = temp_dir / "catalog"
        KnowledgebaseIndexer(_md_config(temp_dir, out)).run()
        alpha = (out / "alpha-domain.md").read_text()
        # how-to header, file-system view with title→location links
        assert "Navigational index built by `kbi`" in alpha
        assert "## File System" in alpha
        assert "[Card A Title](<" in alpha and "thing.caching.kb.md>)" in alpha
        # NO card content is duplicated into the index
        assert "essence of card A" not in alpha
        assert "concept a" not in alpha

    def test_tag_dependency_glossary_views(self, temp_dir):
        _build_cards(temp_dir)
        out = temp_dir / "catalog"
        KnowledgebaseIndexer(_md_config(temp_dir, out)).run()
        alpha = (out / "alpha-domain.md").read_text()
        # tag → locations (shared-tag groups both cards)
        tagsec = alpha.split("## Tags", 1)[1]
        assert "shared-tag" in tagsec and "Card A Title" in tagsec and "Card B Title" in tagsec
        # dependencies: B → A; glossary: foo-term → A
        assert "## Dependencies" in alpha and "builds on: [Card A Title]" in alpha
        assert "## Glossary" in alpha and "foo-term → [Card A Title]" in alpha

    def test_word_index_off_by_default_on_when_forced(self, temp_dir):
        _build_cards(temp_dir)
        out1 = temp_dir / "c1"
        KnowledgebaseIndexer(_md_config(temp_dir, out1)).run()
        assert "## Word Index" not in (out1 / "alpha-domain.md").read_text()
        out2 = temp_dir / "c2"
        KnowledgebaseIndexer(_md_config(temp_dir, out2, views={"word": "on"})).run()
        assert "## Word Index" in (out2 / "alpha-domain.md").read_text()

    def test_view_suppression(self, temp_dir):
        _build_cards(temp_dir)
        out = temp_dir / "catalog"
        KnowledgebaseIndexer(_md_config(temp_dir, out, views={"tag": "off"})).run()
        assert "## Tags" not in (out / "alpha-domain.md").read_text()

    def test_cards_yml_kbyml_raw_ignored(self, temp_dir):
        _build_cards(temp_dir)
        g = KnowledgebaseIndexer(_md_config(temp_dir, temp_dir / "catalog"))
        files = g.discover_files()
        assert len(files) == 3 and all(f.endswith(".kb.md") for f in files)

    def test_no_domain_single_index(self, temp_dir):
        # raw markdown files with no domain → no partition → only INDEX.md
        (temp_dir / "a.md").write_text("# A\n\nalpha content\n", encoding="utf-8")
        (temp_dir / "b.md").write_text("# B\n\nbeta content\n", encoding="utf-8")
        out = temp_dir / "catalog"
        cfg = {
            "directories": {"include": [str(temp_dir)], "exclude": []},
            "keywords": {"files": []},
            "output": {"file": str(out), "format": "markdown"},
            "types": {"include": ["markdown"]},
        }
        KnowledgebaseIndexer(cfg).run()
        assert {p.name for p in out.iterdir()} == {"INDEX.md"}
        index = (out / "INDEX.md").read_text()
        assert "## File System" in index and "## Domains" not in index

    def test_partition_off_forces_flat_despite_domains(self, temp_dir):
        _build_cards(temp_dir)  # cards carry domains
        out = temp_dir / "catalog"
        cfg = _md_config(temp_dir, out)
        cfg["output"]["partition_by_domain"] = "off"
        KnowledgebaseIndexer(cfg).run()
        assert {p.name for p in out.iterdir()} == {"INDEX.md"}      # no per-domain files
        index = (out / "INDEX.md").read_text()
        assert "## File System" in index and "## Domains" not in index

    def test_partition_on_forces_partition_without_domains(self, temp_dir):
        (temp_dir / "a.md").write_text("# A\n\nx\n", encoding="utf-8")  # no domain
        out = temp_dir / "catalog"
        cfg = {
            "directories": {"include": [str(temp_dir)], "exclude": []},
            "keywords": {"files": []},
            "output": {"file": str(out), "format": "markdown", "partition_by_domain": "on"},
            "types": {"include": ["markdown"]},
        }
        KnowledgebaseIndexer(cfg).run()
        assert (out / "none.md").exists()
        assert "[none](none.md)" in (out / "INDEX.md").read_text()


@pytest.mark.integration
class TestFreeplaneModel:
    def test_domain_and_card_view_branches(self, temp_dir):
        _build_cards(temp_dir)
        out = temp_dir / "index.mm"
        cfg = {
            "directories": {"include": [str(temp_dir)], "exclude": []},
            "keywords": {"files": []},
            "output": {"file": str(out), "format": "freeplane"},
            "types": {"include": ["card"]},
        }
        KnowledgebaseIndexer(cfg).run()
        texts = {n.get("TEXT") for n in ET.parse(out).iter("node")}
        assert "Domain: alpha-domain" in texts
        assert "Domain: beta-domain" in texts
        assert "Dependencies" in texts and "Glossary" in texts
