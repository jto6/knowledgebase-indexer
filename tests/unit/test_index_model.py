#!/usr/bin/env python3
"""Unit tests for the index model helpers: view emission and domain resolution."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from index_model import (view_enabled, resolve_domain, marker_comment,
                         file_is_generated, KBI_MARKER_TOKEN)


@pytest.mark.quick
class TestViewEnabled:
    def test_word_is_opt_in_for_both_renderers(self):
        cfg = {"output": {}}
        assert view_enabled(cfg, "word", "freeplane") is False
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
        assert view_enabled(cfg, "word", "freeplane") is False
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


@pytest.mark.quick
class TestProvenanceMarker:
    """The marker lets a later run recognise and skip kbi's own output."""

    def test_comment_is_a_valid_xml_html_comment(self):
        c = marker_comment()
        assert c.startswith("<!--") and c.endswith("-->")
        assert KBI_MARKER_TOKEN in c
        # "--" is illegal inside an XML comment body (Freeplane's loader is picky)
        assert "--" not in c[4:-3]

    def test_detects_marked_file_and_only_reads_head(self, tmp_path):
        f = tmp_path / "INDEX.md"
        f.write_text(marker_comment() + "\n\n# Title\n", encoding="utf-8")
        assert file_is_generated(str(f)) is True

    def test_plain_source_is_not_flagged(self, tmp_path):
        f = tmp_path / "real.md"
        f.write_text("# Real content\n\nnothing special here\n", encoding="utf-8")
        assert file_is_generated(str(f)) is False

    def test_marker_below_head_window_is_not_matched(self, tmp_path):
        # A genuine doc that merely mentions the token deep in its body is source.
        f = tmp_path / "doc.md"
        f.write_text("# Doc\n\n" + ("x " * 5000) + KBI_MARKER_TOKEN + "\n",
                     encoding="utf-8")
        assert file_is_generated(str(f), max_bytes=64) is False

    def test_missing_file_is_not_generated(self, tmp_path):
        assert file_is_generated(str(tmp_path / "nope.md")) is False

    def test_generated_mm_is_well_formed_and_marked(self, tmp_path):
        import xml.dom.minidom as minidom
        from mindmap_generator import FreeplaneMapGenerator
        out = tmp_path / "out.mm"
        FreeplaneMapGenerator(str(out)).create_mind_map(
            {"README.md": [], "src/a.py": []}, [], {}, {}, {})
        text = out.read_text(encoding="utf-8")
        minidom.parseString(text)                    # must parse (loader proxy)
        assert KBI_MARKER_TOKEN in text
        assert file_is_generated(str(out)) is True
        # marker sits just inside <map>, before the root node (Freeplane's spot)
        lines = text.splitlines()
        assert lines[0].lstrip().startswith("<map")
        assert KBI_MARKER_TOKEN in lines[1]

    def test_discovery_skips_a_generated_index_in_the_tree(self, tmp_path):
        """A kbi-generated .mm sitting inside a scanned tree is not re-indexed."""
        from kbi import KnowledgebaseIndexer
        from mindmap_generator import FreeplaneMapGenerator
        # A real source map and a generated index, side by side in the tree.
        (tmp_path / "real.md").write_text("# Real\n\ncontent\n", encoding="utf-8")
        gen = tmp_path / "old_index.mm"
        FreeplaneMapGenerator(str(gen)).create_mind_map({"a.md": []}, [], {}, {}, {})
        cfg = {"directories": {"include": [str(tmp_path)]},
               "output": {"file": str(tmp_path / "new.mm"), "format": "freeplane"}}
        found = KnowledgebaseIndexer(cfg).discover_files()
        assert str(tmp_path / "real.md") in found
        assert str(gen) not in found
