#!/usr/bin/env python3
"""
Unit tests for the CardHandler and card-aware indexing (increment A).

Covers:
- `.kb.md` recognition (can_handle / validate_file)
- frontmatter + essence parsing into a card record
- card-aware tag extraction (frontmatter tags labeled by card title)
- handler precedence (compound `.kb.md` wins over `.md`)
- config `file_types` replace semantics (enables distilled-only scope)
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import ConfigLoader
from core_handlers import HandlerRegistry
from handlers.card_handler import CardHandler
from handlers.markdown_handler import MarkdownHandler


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
class TestFileTypesReplaceSemantics:
    def test_explicit_file_types_replace_defaults(self):
        """A card-only config must NOT inherit the default markdown/freeplane
        types, otherwise distilled-only scoping is impossible."""
        loader = ConfigLoader()
        user = {
            "directories": {"include": ["."]},
            "output": {"file": "out.mm"},
            "file_types": {"card": {"extensions": [".kb.md"], "handler": "CardHandler"}},
        }
        merged = loader._merge_with_defaults(user)
        assert set(merged["file_types"].keys()) == {"card"}

    def test_defaults_used_when_file_types_absent(self):
        loader = ConfigLoader()
        user = {"directories": {"include": ["."]}, "output": {"file": "out.mm"}}
        merged = loader._merge_with_defaults(user)
        assert "markdown" in merged["file_types"]
        assert "freeplane" in merged["file_types"]
