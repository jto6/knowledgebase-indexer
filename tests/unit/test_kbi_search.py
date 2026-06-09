#!/usr/bin/env python3
"""Tests for `kbi search` (built-in grep over the indexed file set) and for the
word index being opt-in and not computed unless enabled (D20)."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kbi import KnowledgebaseIndexer, run_search
from mindmap_generator import FreeplaneMapGenerator


def _tree(tmp_path):
    """A small tree: two markdown sources plus a generated .mm index."""
    (tmp_path / "alpha.md").write_text("# Alpha\n\nthe needle is here\n", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# Beta\n\nnothing of interest\n", encoding="utf-8")
    gen = tmp_path / "old_index.mm"
    FreeplaneMapGenerator(str(gen)).create_mind_map({"x.md": []}, [], {}, {}, {})
    return gen


def _cfg_file(tmp_path):
    cfg = {
        "directories": {"include": [str(tmp_path)], "exclude": []},
        "keywords": {"files": []},
        "output": {"file": str(tmp_path / "out.mm"), "format": "freeplane"},
    }
    path = tmp_path / "kbi.yml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


@pytest.mark.quick
class TestSearch:
    def test_match_returns_zero_and_prints_file(self, tmp_path, capfd):
        _tree(tmp_path)
        cfg = _cfg_file(tmp_path)
        rc = run_search([str(cfg), "needle", "-l"])
        out = capfd.readouterr().out
        assert rc == 0
        assert "alpha.md" in out
        assert "beta.md" not in out

    def test_no_match_returns_one(self, tmp_path):
        _tree(tmp_path)
        cfg = _cfg_file(tmp_path)
        assert run_search([str(cfg), "zzz_no_such_token_qqq"]) == 1

    def test_bad_config_returns_two(self, tmp_path):
        assert run_search([str(tmp_path / "nope.yml"), "x"]) == 2

    def test_does_not_search_generated_index(self, tmp_path, capfd):
        """The generated .mm is skipped by discovery, so its node text is unsearched."""
        gen = _tree(tmp_path)
        cfg = _cfg_file(tmp_path)
        # "Navigation Index" exists only inside the generated map.
        rc = run_search([str(cfg), "Navigation Index"])
        assert rc == 1
        assert str(gen) not in capfd.readouterr().out


@pytest.mark.quick
class TestWordIndexOptIn:
    def _indexer_over(self, tmp_path, views=None):
        (tmp_path / "doc.md").write_text("# Doc\n\nalpha beta gamma\n", encoding="utf-8")
        cfg = {
            "directories": {"include": [str(tmp_path)], "exclude": []},
            "keywords": {"files": []},
            "output": {"file": str(tmp_path / "o.mm"), "format": "freeplane"},
        }
        if views is not None:
            cfg["output"]["views"] = views
        return KnowledgebaseIndexer(cfg)

    def test_word_not_computed_by_default(self, tmp_path, monkeypatch):
        g = self._indexer_over(tmp_path)
        calls = {"n": 0}
        real = g.extract_significant_words

        def spy(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(g, "extract_significant_words", spy)
        files = g.discover_files()
        model = g.build_index_model(files, g.create_file_handlers(files))
        assert calls["n"] == 0
        assert all(not di.words for di in model.domains.values())

    def test_word_computed_when_enabled(self, tmp_path, monkeypatch):
        g = self._indexer_over(tmp_path, views={"word": "on"})
        calls = {"n": 0}
        real = g.extract_significant_words

        def spy(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(g, "extract_significant_words", spy)
        files = g.discover_files()
        g.build_index_model(files, g.create_file_handlers(files))
        assert calls["n"] >= 1   # the gate runs the (expensive) computation
