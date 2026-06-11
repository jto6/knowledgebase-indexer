#!/usr/bin/env python3
"""
Unit tests for the CardHandler and card-aware indexing (increment A).

Covers:
- `.kb.md` recognition (can_handle / validate_file)
- frontmatter + essence parsing into a card record
- card-aware tag extraction (frontmatter tags labeled by card title)
- handler precedence (compound `.kb.md` wins over `.md`)
- built-in type selection and most-specific classification (`types` include/exclude)
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import ConfigLoader
from core_handlers import HandlerRegistry
from handlers.card_handler import CardHandler
from handlers.markdown_handler import MarkdownHandler
from kbi import KnowledgebaseIndexer


CARD_TEXT = """---
id: 11111111-1111-1111-1111-111111111111
slug: test-card
title: Test Card Title
source: ../Plan.md
domain: spiritual
tags: [alpha, beta, gamma]
builds_on: [other-card]
defines: [some-term]
meta:
  scripture: ["John 3:16"]
---

# Test Card Title

> This is the essence line,
> spanning two lines.

## Core Concepts

- a concept
\t- detail
"""


@pytest.fixture
def card_file(tmp_path):
    """Write a card and a plain markdown file; return their paths."""
    kb = tmp_path / ".kb"
    kb.mkdir()
    card = kb / "Plan.kb.md"
    card.write_text(CARD_TEXT, encoding="utf-8")
    plain = tmp_path / "Plan.md"
    plain.write_text("# Plain\n\nNo frontmatter here.\n", encoding="utf-8")
    return {"card": str(card), "plain": str(plain)}


@pytest.fixture
def card_handler():
    return CardHandler({"extensions": [".kb.md"]})


@pytest.mark.quick
class TestCardRecognition:
    def test_can_handle_card(self, card_handler, card_file):
        assert card_handler.can_handle(card_file["card"]) is True

    def test_does_not_handle_plain_markdown(self, card_handler, card_file):
        assert card_handler.can_handle(card_file["plain"]) is False

    def test_validate_file_accepts_compound_suffix(self, card_handler, card_file):
        # base FileHandler.validate_file checks path.suffix (==".md") and would
        # reject; CardHandler must accept by full-name suffix match.
        assert card_handler.validate_file(card_file["card"]) is True
        assert card_handler.validate_file(card_file["plain"]) is False


@pytest.mark.quick
class TestCardRecordParsing:
    def test_frontmatter_fields(self, card_handler, card_file):
        rec = card_handler.get_card_record(card_file["card"])
        assert rec["id"] == "11111111-1111-1111-1111-111111111111"
        assert rec["slug"] == "test-card"
        assert rec["title"] == "Test Card Title"
        assert rec["tags"] == ["alpha", "beta", "gamma"]
        assert rec["builds_on"] == ["other-card"]
        assert rec["defines"] == ["some-term"]
        assert rec["meta"]["scripture"] == ["John 3:16"]

    def test_essence_is_joined_blockquote(self, card_handler, card_file):
        rec = card_handler.get_card_record(card_file["card"])
        assert rec["essence"] == "This is the essence line, spanning two lines."

    def test_record_without_frontmatter_falls_back_to_filename(self, card_handler, tmp_path):
        f = tmp_path / "Bare.kb.md"
        f.write_text("# Bare\n\nNo frontmatter.\n", encoding="utf-8")
        rec = card_handler.get_card_record(str(f))
        assert rec["title"] == "Bare.kb.md"
        assert rec["essence"] == ""


@pytest.mark.quick
class TestCardAwareTags:
    def test_tags_come_from_frontmatter_labeled_by_title(self, card_handler, card_file):
        tag_map = card_handler.extract_tags(card_file["card"])
        assert set(tag_map.keys()) == {"alpha", "beta", "gamma"}
        # each tag points at the file, file-level node id, labeled by card title
        for matches in tag_map.values():
            assert matches == [(card_file["card"], "", "Test Card Title")]


@pytest.mark.quick
class TestHandlerPrecedence:
    @pytest.mark.parametrize("order", [("markdown", "card"), ("card", "markdown")])
    def test_card_wins_over_markdown_regardless_of_order(self, card_file, order):
        registry = HandlerRegistry()
        registry.register_handler("MarkdownHandler", MarkdownHandler)
        registry.register_handler("CardHandler", CardHandler)
        types = {
            "markdown": {"extensions": [".md", ".markdown"], "handler": "MarkdownHandler"},
            "card": {"extensions": [".kb.md"], "handler": "CardHandler"},
        }
        ordered = {k: types[k] for k in order}
        handler = registry.get_handler_for_file(card_file["card"], ordered)
        assert isinstance(handler, CardHandler)

    def test_plain_markdown_still_goes_to_markdown(self, card_file):
        registry = HandlerRegistry()
        registry.register_handler("MarkdownHandler", MarkdownHandler)
        registry.register_handler("CardHandler", CardHandler)
        types = {
            "markdown": {"extensions": [".md", ".markdown"], "handler": "MarkdownHandler"},
            "card": {"extensions": [".kb.md"], "handler": "CardHandler"},
        }
        handler = registry.get_handler_for_file(card_file["plain"], types)
        assert isinstance(handler, MarkdownHandler)


@pytest.mark.quick
class TestTypeSelection:
    """Built-in types are selected by name via `types` include/exclude; a file is
    classified by its most-specific type."""

    def _indexer(self, types=None):
        from kbi import KnowledgebaseIndexer
        cfg = {"directories": {"include": ["."]}, "output": {"file": "o", "format": "markdown"}}
        if types is not None:
            cfg["types"] = types
        return KnowledgebaseIndexer(cfg)

    def test_classify_most_specific(self):
        g = self._indexer()
        assert g._type_of("foo.kb.md") == "card"     # not markdown
        assert g._type_of("foo.md") == "markdown"
        assert g._type_of("foo.mm") == "freeplane"
        assert g._type_of("foo.pdf") is None

    def test_enabled_types_default_include_exclude(self):
        assert set(self._indexer()._enabled_types()) == {"card", "markdown", "freeplane"}
        assert self._indexer({"include": ["card"]})._enabled_types() == ["card"]
        assert set(self._indexer({"exclude": ["card"]})._enabled_types()) == {"markdown", "freeplane"}


@pytest.mark.quick
class TestExportedAs:
    """Format-export pairs: `exported_as` field parsed and export paths suppressed from FS view."""

    CARD_WITH_EXPORT = """---
title: Slide Deck
source: ../reports/deck.pptx
exported_as:
  - ../reports/deck.pdf
---

# Slide Deck

> Overview of the project.
"""

    def _indexer(self):
        cfg = {"directories": {"include": ["."]}, "output": {"file": "o", "format": "markdown"}}
        return KnowledgebaseIndexer(cfg)

    def test_resolve_exported_as_returns_absolute_paths(self, tmp_path):
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Deck.kb.md"
        card.write_text(self.CARD_WITH_EXPORT, encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        paths = KnowledgebaseIndexer._resolve_exported_as(rec)
        assert len(paths) == 1
        assert paths[0] == str((tmp_path / "reports" / "deck.pdf").resolve())

    def test_resolve_exported_as_empty_when_absent(self, tmp_path):
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "NoExport.kb.md"
        card.write_text("---\ntitle: Plain\nsource: ../doc.md\n---\n# Plain\n", encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        assert KnowledgebaseIndexer._resolve_exported_as(rec) == []

    def test_exported_as_suppressed_from_fs_view(self, tmp_path):
        """A file listed in exported_as must not appear in build_file_system_index."""
        # Set up: source .pptx, exported .pdf, and a card pointing to both.
        reports = tmp_path / "reports"; reports.mkdir()
        pptx = reports / "deck.pptx"; pptx.write_text("(binary)", encoding="utf-8")
        pdf = reports / "deck.pdf"; pdf.write_text("(binary)", encoding="utf-8")
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Deck.kb.md"
        card.write_text(self.CARD_WITH_EXPORT, encoding="utf-8")

        indexer = self._indexer()
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        exported = set(KnowledgebaseIndexer._resolve_exported_as(rec))

        from handlers.markdown_handler import MarkdownHandler
        md_handler = MarkdownHandler({"extensions": [".md"]})
        # Simulate the handlers dict with a non-card handler for the pdf path.
        # (In real use the pdf would have no handler; here we use markdown as a
        # stand-in to verify the suppression logic, not handler assignment.)
        handlers = {str(pdf): md_handler}
        fs = indexer.build_file_system_index([str(pdf)], handlers, exported)
        assert str(pdf) not in fs

    def test_exported_as_stored_in_card_group(self, tmp_path):
        """build_card_groups populates CardGroup.exported_as from the card record."""
        reports = tmp_path / "reports"; reports.mkdir()
        (reports / "deck.pptx").write_text("", encoding="utf-8")
        pdf = reports / "deck.pdf"; pdf.write_text("", encoding="utf-8")
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Deck.kb.md"
        card.write_text(self.CARD_WITH_EXPORT, encoding="utf-8")

        indexer = self._indexer()
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        card_records = {str(card): rec}
        groups = indexer.build_card_groups([str(card)], card_records)

        # The group keyed by the source path must list the pdf as exported_as.
        source_path = str((tmp_path / "reports" / "deck.pptx").resolve())
        assert source_path in groups
        assert str(pdf.resolve()) in groups[source_path].exported_as


@pytest.mark.quick
class TestRefines:
    """Near-duplicate/refinement: `refines` field parsed and superseded paths suppressed from FS view."""

    CARD_WITH_REFINES = """---
title: Spec Final
source: ../docs/spec_final.md
refines:
  - ../docs/spec_v1.md
  - ../docs/spec_draft.md
---

# Spec Final

> The definitive specification.
"""

    def _indexer(self):
        cfg = {"directories": {"include": ["."]}, "output": {"file": "o", "format": "markdown"}}
        return KnowledgebaseIndexer(cfg)

    def test_resolve_refines_returns_absolute_paths(self, tmp_path):
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Spec.kb.md"
        card.write_text(self.CARD_WITH_REFINES, encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        paths = KnowledgebaseIndexer._resolve_refines(rec)
        assert len(paths) == 2
        assert paths[0] == str((tmp_path / "docs" / "spec_v1.md").resolve())
        assert paths[1] == str((tmp_path / "docs" / "spec_draft.md").resolve())

    def test_resolve_refines_empty_when_absent(self, tmp_path):
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "NoRefines.kb.md"
        card.write_text("---\ntitle: Plain\nsource: ../doc.md\n---\n# Plain\n", encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        assert KnowledgebaseIndexer._resolve_refines(rec) == []

    def test_superseded_sources_suppressed_from_fs_view(self, tmp_path):
        """Files listed in refines must not appear in build_file_system_index."""
        docs = tmp_path / "docs"; docs.mkdir()
        v1 = docs / "spec_v1.md"; v1.write_text("# v1\n", encoding="utf-8")
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Spec.kb.md"
        card.write_text(self.CARD_WITH_REFINES, encoding="utf-8")

        indexer = self._indexer()
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        absorbed = set(KnowledgebaseIndexer._resolve_refines(rec))

        from handlers.markdown_handler import MarkdownHandler
        md_handler = MarkdownHandler({"extensions": [".md"]})
        handlers = {str(v1): md_handler}
        fs = indexer.build_file_system_index([str(v1)], handlers, absorbed)
        assert str(v1) not in fs

    def test_refines_stored_in_card_group(self, tmp_path):
        """build_card_groups populates CardGroup.refines from the card record."""
        docs = tmp_path / "docs"; docs.mkdir()
        final = docs / "spec_final.md"; final.write_text("# Final\n", encoding="utf-8")
        v1 = docs / "spec_v1.md"; v1.write_text("# v1\n", encoding="utf-8")
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Spec.kb.md"
        card.write_text(self.CARD_WITH_REFINES, encoding="utf-8")

        indexer = self._indexer()
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        card_records = {str(card): rec}
        groups = indexer.build_card_groups([str(card)], card_records)

        source_path = str(final.resolve())
        assert source_path in groups
        assert str(v1.resolve()) in groups[source_path].refines


@pytest.mark.quick
class TestDirSummary:
    """Directory-summary cards: recognized, dir annotation extracted, not in card_groups."""

    DIR_SUMMARY_CARD = """---
title: Reports Directory
kind: dir_summary
source: ..
---

# Reports Directory

> A collection of quarterly financial reports.
"""

    def _indexer(self):
        cfg = {"directories": {"include": ["."]}, "output": {"file": "o", "format": "markdown"}}
        return KnowledgebaseIndexer(cfg)

    def test_is_dir_summary_true_for_dir_summary_kind(self, tmp_path):
        from handlers.card_handler import is_dir_summary
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "reports.kb.md"
        card.write_text(self.DIR_SUMMARY_CARD, encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        assert is_dir_summary(rec) is True

    def test_is_dir_summary_false_for_topic_card(self, tmp_path):
        from handlers.card_handler import is_dir_summary
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Plan.kb.md"
        card.write_text("---\ntitle: Plan\nsource: ../Plan.md\n---\n# Plan\n\n> A plan.\n",
                        encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        assert is_dir_summary(rec) is False

    def test_dir_summary_not_in_card_groups(self, tmp_path):
        """build_card_groups must skip dir_summary cards entirely."""
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "reports.kb.md"
        card.write_text(self.DIR_SUMMARY_CARD, encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        indexer = self._indexer()
        groups = indexer.build_card_groups([str(card)], {str(card): rec})
        assert groups == {}

    def test_dir_annotation_extracted_from_dir_summary_card(self, tmp_path):
        """build_dir_annotations produces an abs_dir → essence entry."""
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "reports.kb.md"
        card.write_text(self.DIR_SUMMARY_CARD, encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        indexer = self._indexer()
        annotations = indexer.build_dir_annotations([str(card)], {str(card): rec})
        expected_dir = str(tmp_path.resolve())
        assert expected_dir in annotations
        assert annotations[expected_dir] == "A collection of quarterly financial reports."

    def test_no_annotation_when_no_dir_summary(self, tmp_path):
        """build_dir_annotations returns empty dict when no dir_summary cards are present."""
        kb = tmp_path / ".kb"; kb.mkdir()
        card = kb / "Plan.kb.md"
        card.write_text("---\ntitle: Plan\nsource: ../Plan.md\n---\n# Plan\n\n> A plan.\n",
                        encoding="utf-8")
        handler = CardHandler({"extensions": [".kb.md"]})
        rec = handler.get_card_record(str(card))
        indexer = self._indexer()
        annotations = indexer.build_dir_annotations([str(card)], {str(card): rec})
        assert annotations == {}
