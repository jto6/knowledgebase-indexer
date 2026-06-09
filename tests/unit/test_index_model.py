#!/usr/bin/env python3
"""Unit tests for the index model helpers: view emission and domain resolution."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from index_model import view_enabled, resolve_domain


@pytest.mark.quick
class TestViewEnabled:
    def test_word_default_differs_by_renderer(self):
        cfg = {"output": {}}
        assert view_enabled(cfg, "word", "freeplane") is True
        assert view_enabled(cfg, "word", "markdown") is False

    def test_other_views_default_on(self):
        cfg = {"output": {}}
        for v in ("file_system", "keyword", "tag", "dependencies", "glossary"):
            assert view_enabled(cfg, v, "markdown") is True
            assert view_enabled(cfg, v, "freeplane") is True

    def test_on_off_override_defaults(self):
        on = {"output": {"views": {"word": "on", "tag": "off"}}}
        assert view_enabled(on, "word", "markdown") is True       # forced on
        assert view_enabled(on, "tag", "freeplane") is False      # forced off

    def test_auto_is_default(self):
        cfg = {"output": {"views": {"word": "auto"}}}
        assert view_enabled(cfg, "word", "freeplane") is True
        assert view_enabled(cfg, "word", "markdown") is False


@pytest.mark.quick
class TestResolveDomain:
    def test_card_frontmatter_domain_wins(self, tmp_path):
        rec = {"domain": "spiritual"}
        assert resolve_domain(str(tmp_path / "x.kb.md"), rec) == "spiritual"

    def test_non_card_uses_nearest_kbyml(self, tmp_path):
        (tmp_path / ".kb").mkdir()
        (tmp_path / ".kb" / "kb.yml").write_text("domain: technical\n", encoding="utf-8")
        sub = tmp_path / "sub"; sub.mkdir()
        assert resolve_domain(str(sub / "raw.md"), None) == "technical"

    def test_no_domain_anywhere_returns_none(self, tmp_path):
        assert resolve_domain(str(tmp_path / "raw.md"), None) is None
