#!/usr/bin/env python3
"""
Unit tests for the Markdown slice renderer (increment B).

Covers per-domain slicing, the overview INDEX, builds_on slug→title resolution,
the defined-term glossary, tag clustering, and frontmatter-field normalization.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from markdown_slice_renderer import MarkdownSliceRenderer, _as_list


def sample_records():
    return [
        {
            "slug": "a", "title": "Alpha", "domain": "spiritual",
            "essence": "essence of alpha", "tags": ["faith", "grace"],
            "defines": ["term-x"], "file_path": "/x/a.kb.md", "source": "../Plan.md",
        },
        {
            "slug": "b", "title": "Beta", "domain": "spiritual",
            "essence": "essence of beta", "tags": ["grace"],
            "builds_on": ["a"], "file_path": "/x/b.kb.md",
        },
        {
            "slug": "c", "title": "Gamma", "domain": "technical",
            "tags": ["architecture"], "file_path": "/y/c.kb.md",
        },
    ]


@pytest.mark.quick
class TestSliceRendering:
    def test_writes_one_slice_per_domain_plus_index(self, tmp_path):
        written = MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        names = {Path(p).name for p in written}
        assert names == {"spiritual.md", "technical.md", "INDEX.md"}
        assert (tmp_path / "spiritual.md").exists()

    def test_overview_lists_domains_with_counts(self, tmp_path):
        MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        index = (tmp_path / "INDEX.md").read_text()
        assert "[spiritual](spiritual.md) — 2 card(s)" in index
        assert "[technical](technical.md) — 1 card(s)" in index

    def test_card_entry_contains_essence_tags_and_path(self, tmp_path):
        MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        slice_text = (tmp_path / "spiritual.md").read_text()
        assert "- Alpha" in slice_text
        assert "essence of alpha" in slice_text
        assert "tags: faith, grace" in slice_text
        assert "/x/a.kb.md" in slice_text

    def test_builds_on_resolves_slug_to_title(self, tmp_path):
        MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        slice_text = (tmp_path / "spiritual.md").read_text()
        # Beta builds_on slug "a" -> rendered as Alpha's title, not the raw slug
        assert "builds on: Alpha" in slice_text

    def test_glossary_maps_term_to_defining_card(self, tmp_path):
        MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        slice_text = (tmp_path / "spiritual.md").read_text()
        assert "## Glossary (defined terms)" in slice_text
        assert "term-x — Alpha (/x/a.kb.md)" in slice_text

    def test_tag_clusters_cards(self, tmp_path):
        MarkdownSliceRenderer(str(tmp_path)).render(sample_records())
        slice_text = (tmp_path / "spiritual.md").read_text()
        # the "grace" tag groups both Alpha and Beta under it
        grace_section = slice_text.split("- grace", 1)[1]
        assert "Alpha" in grace_section.split("##", 1)[0]
        assert "Beta" in grace_section.split("##", 1)[0]

    def test_missing_domain_falls_back_to_uncategorized(self, tmp_path):
        records = [{"slug": "z", "title": "NoDomain", "file_path": "/z/z.kb.md"}]
        MarkdownSliceRenderer(str(tmp_path)).render(records)
        assert (tmp_path / "uncategorized.md").exists()

    def test_list_source_renders_all_entries(self, tmp_path):
        """A captured remote source has a list `source` (URL + local transcript);
        the slice must render every entry."""
        records = [{
            "slug": "sermon", "title": "A Sermon", "domain": "spiritual",
            "essence": "e", "tags": ["grace"], "file_path": "/s/.kb/sermon.kb.md",
            "source": ["https://youtu.be/XYZ", "../sermon.md"],
        }]
        MarkdownSliceRenderer(str(tmp_path)).render(records)
        slice_text = (tmp_path / "spiritual.md").read_text()
        assert "source: https://youtu.be/XYZ, ../sermon.md" in slice_text


@pytest.mark.quick
class TestNormalization:
    def test_as_list_handles_list_str_and_none(self):
        assert _as_list(["a", "b"]) == ["a", "b"]
        assert _as_list("a, b ,c") == ["a", "b", "c"]
        assert _as_list(None) == []
        assert _as_list("solo") == ["solo"]
