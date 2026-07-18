#!/usr/bin/env python3
"""
Unit tests for the --update staleness check and refresh loop helpers.

Covers _dir_content_changed (absorbed-source handling, new/changed/deleted
sources), _is_budget_exhausted, and _commit_kb_updates (pathspec-confined
git commit).
"""

import hashlib
import subprocess
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kbi import KnowledgebaseIndexer


def _sha(path: Path) -> str:
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def _make_dir(tmp_path: Path, files: dict) -> Path:
    """Create a source dir with a .kb/ subdir and the given {name: content} files."""
    (tmp_path / '.kb').mkdir()
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    return tmp_path


@pytest.mark.quick
class TestDirContentChanged:
    """Staleness check against a segmentation manifest dict."""

    def test_unchanged_sources_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'source_hash': _sha(d / 'A.mm')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_superseded_file_on_disk_not_stale(self, tmp_path):
        # Regression: a still-present superseded file (e.g. SDV2.mm) must not
        # look like a new untracked source.
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'alpha v1'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'supersedes': ['../A_old.mm'],
                          'source_hash': _sha(d / 'A.mm')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_exported_as_file_on_disk_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.md': 'alpha', 'A_export.md': 'alpha export'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.md',
                          'exported_as': ['../A_export.md'],
                          'source_hash': _sha(d / 'A.md')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_absorbed_md_link_form_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A old.mm': 'alpha v1'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'supersedes': ['[A old.mm](<../A old.mm>)'],
                          'source_hash': _sha(d / 'A.mm')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_new_tracked_ext_file_is_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'B.mm': 'brand new'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'source_hash': _sha(d / 'A.mm')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is True

    def test_changed_source_is_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'source_hash': _sha(d / 'A.mm')}]}
        (d / 'A.mm').write_text('alpha changed')
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is True

    def test_deleted_source_is_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'source_hash': _sha(d / 'A.mm')}]}
        (d / 'A.mm').unlink()
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is True

    def test_absorbed_ext_does_not_broaden_tracking(self, tmp_path):
        # A .pdf known only via exported_as must not make other .pdf files
        # count as new sources (tracked_exts comes from card sources only).
        d = _make_dir(tmp_path, {'A.md': 'alpha', 'A.pdf': 'pdf export',
                                 'other.pdf': 'unrelated pdf'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.md',
                          'exported_as': ['../A.pdf'],
                          'source_hash': _sha(d / 'A.md')}]}
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False


@pytest.mark.quick
class TestExcludedSection:
    """Phase 2: `excluded:` manifest entries are durable decisions."""

    def _seg(self, d: Path, excluded) -> dict:
        return {'cards': [{'slug': 'a', 'source': '../A.mm',
                           'source_hash': _sha(d / 'A.mm')}],
                'excluded': excluded}

    def test_excluded_file_unchanged_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'Delme.mm': 'scratch'})
        seg = self._seg(d, [{'path': '../Delme.mm', 'reason': 'disposable',
                             'source_hash': _sha(d / 'Delme.mm')}])
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_excluded_file_edited_is_stale(self, tmp_path):
        # Drift re-opens the exclusion decision.
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'Delme.mm': 'scratch'})
        seg = self._seg(d, [{'path': '../Delme.mm', 'reason': 'disposable',
                             'source_hash': _sha(d / 'Delme.mm')}])
        (d / 'Delme.mm').write_text('scratch grown into real content')
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is True

    def test_excluded_file_deleted_not_stale(self, tmp_path):
        # Deletion prunes the entry at the next reconcile; nothing to re-decide.
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'Delme.mm': 'scratch'})
        seg = self._seg(d, [{'path': '../Delme.mm', 'reason': 'disposable',
                             'source_hash': _sha(d / 'Delme.mm')}])
        (d / 'Delme.mm').unlink()
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_excluded_entry_without_hash_not_stale(self, tmp_path):
        # Bare-string form: excluded regardless, no hash tracked.
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'Delme.mm': 'scratch'})
        seg = self._seg(d, ['../Delme.mm'])
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False


@pytest.mark.quick
class TestHashedAbsorbedEntries:
    """Phase 2: dict-form supersedes/exported_as entries re-open on drift."""

    def _seg(self, d: Path, supersedes) -> dict:
        return {'cards': [{'slug': 'a', 'source': '../A.mm',
                           'supersedes': supersedes,
                           'source_hash': _sha(d / 'A.mm')}]}

    def test_hashed_superseded_unchanged_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'alpha v1'})
        seg = self._seg(d, [{'path': '../A_old.mm',
                             'source_hash': _sha(d / 'A_old.mm')}])
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_hashed_superseded_edited_is_stale(self, tmp_path):
        # Editing a superseded file re-opens the supersession decision.
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'alpha v1'})
        seg = self._seg(d, [{'path': '../A_old.mm',
                             'source_hash': _sha(d / 'A_old.mm')}])
        (d / 'A_old.mm').write_text('diverged into its own document')
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is True

    def test_hashed_superseded_deleted_not_stale(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'alpha v1'})
        seg = self._seg(d, [{'path': '../A_old.mm',
                             'source_hash': _sha(d / 'A_old.mm')}])
        (d / 'A_old.mm').unlink()
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False

    def test_truncated_hash_prefix_accepted(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'alpha v1'})
        seg = self._seg(d, [{'path': '../A_old.mm',
                             'source_hash': _sha(d / 'A_old.mm')[:23]}])
        assert KnowledgebaseIndexer._dir_content_changed(seg, d / '.kb') is False


@pytest.mark.quick
class TestBudgetDetection:

    def test_spend_limit_message(self):
        out = "You've hit your monthly spend limit · raise it at claude.ai/settings/usage"
        assert KnowledgebaseIndexer._is_budget_exhausted(out) is True

    def test_usage_limit_message(self):
        assert KnowledgebaseIndexer._is_budget_exhausted(
            'You have reached your usage limit') is True

    def test_benign_output(self):
        assert KnowledgebaseIndexer._is_budget_exhausted(
            'Reconciled. 3 cards refreshed.') is False


@pytest.mark.quick
class TestCommitKbUpdates:

    def _init_repo(self, tmp_path: Path) -> Path:
        def git(*args):
            subprocess.run(['git', '-C', str(tmp_path), *args],
                           check=True, capture_output=True, text=True)
        subprocess.run(['git', 'init', '-q', str(tmp_path)],
                       check=True, capture_output=True)
        git('config', 'user.name', 'Test User')
        git('config', 'user.email', 'test@example.com')
        (tmp_path / 'source.md').write_text('source')
        git('add', '.')
        git('commit', '-q', '-m', 'initial')
        return tmp_path

    def test_commits_only_kb_paths(self, tmp_path):
        repo = self._init_repo(tmp_path)
        kb = repo / '.kb'
        kb.mkdir()
        (kb / 'segmentation.yml').write_text('version: 1\n')
        (kb / 'a.kb.md').write_text('# A\n')
        # Unrelated changes: one staged, one unstaged — neither may be committed.
        (repo / 'source.md').write_text('modified source')
        (repo / 'staged.txt').write_text('pre-staged')
        subprocess.run(['git', '-C', str(repo), 'add', 'staged.txt'],
                       check=True, capture_output=True)

        KnowledgebaseIndexer._commit_kb_updates(str(repo))

        show = subprocess.run(
            ['git', '-C', str(repo), 'show', '--stat', '--name-only',
             '--format=%s%n%(trailers)', 'HEAD'],
            capture_output=True, text=True).stdout
        assert 'kb: refresh knowledge cards' in show
        assert 'Signed-off-by: Test User <test@example.com>' in show
        assert '.kb/segmentation.yml' in show
        assert '.kb/a.kb.md' in show
        assert 'source.md' not in show
        assert 'staged.txt' not in show
        # The pre-staged unrelated file must remain staged, not be lost.
        staged = subprocess.run(
            ['git', '-C', str(repo), 'diff', '--cached', '--name-only'],
            capture_output=True, text=True).stdout
        assert 'staged.txt' in staged

    def test_noop_when_kb_clean(self, tmp_path):
        repo = self._init_repo(tmp_path)
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True).stdout
        KnowledgebaseIndexer._commit_kb_updates(str(repo))
        head2 = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                               capture_output=True, text=True).stdout
        assert head == head2

    def test_noop_outside_work_tree(self, tmp_path):
        (tmp_path / '.kb').mkdir()
        (tmp_path / '.kb' / 'a.kb.md').write_text('# A\n')
        # Must simply return without raising.
        KnowledgebaseIndexer._commit_kb_updates(str(tmp_path))

    def test_respects_update_commit_false(self, tmp_path):
        repo = self._init_repo(tmp_path)
        kb = repo / '.kb'
        kb.mkdir()
        (kb / 'kb.yml').write_text('domain: test\nupdate_commit: false\n')
        (kb / 'a.kb.md').write_text('# A\n')
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True).stdout
        KnowledgebaseIndexer._commit_kb_updates(str(repo))
        head2 = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                               capture_output=True, text=True).stdout
        assert head == head2
