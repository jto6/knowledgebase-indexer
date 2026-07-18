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
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kbi import KnowledgebaseIndexer, run_hash, run_manifest_sync, _compute_dir_hash


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
class TestDirContentDelta:
    """Phase 3: the delta handoff payload."""

    def test_full_delta_shape(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'B.mm': 'beta',
                                 'C.mm': 'gamma', 'New.mm': 'brand new'})
        seg = {'cards': [
            {'slug': 'a1', 'source': '../A.mm', 'source_hash': _sha(d / 'A.mm')},
            {'slug': 'a2', 'source': '../A.mm', 'source_hash': _sha(d / 'A.mm')},
            {'slug': 'b', 'source': '../B.mm', 'source_hash': _sha(d / 'B.mm')},
            {'slug': 'c', 'source': '../C.mm', 'source_hash': _sha(d / 'C.mm')},
        ]}
        old_b = _sha(d / 'B.mm')
        (d / 'B.mm').write_text('beta changed')
        (d / 'C.mm').unlink()

        delta = KnowledgebaseIndexer._dir_content_delta(seg, d / '.kb')

        assert delta['bootstrap'] is False
        assert delta['unchanged'] == 1  # A.mm (two cards, one source)
        assert delta['changed'] == [{'path': 'B.mm', 'old_hash': old_b,
                                     'new_hash': _sha(d / 'B.mm'), 'cards': ['b']}]
        assert delta['deleted'] == [{'path': 'C.mm', 'cards': ['c']}]
        assert delta['new'] == ['New.mm']
        assert delta['reopened'] == []

    def test_bootstrap_delta(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha'})
        delta = KnowledgebaseIndexer._dir_content_delta({'cards': []}, d / '.kb')
        assert delta['bootstrap'] is True
        assert KnowledgebaseIndexer._delta_has_drift(delta) is True

    def test_reopened_carries_decision_context(self, tmp_path):
        d = _make_dir(tmp_path, {'A.mm': 'alpha', 'A_old.mm': 'v1',
                                 'Delme.mm': 'scratch'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm',
                          'supersedes': [{'path': '../A_old.mm',
                                          'source_hash': _sha(d / 'A_old.mm')}],
                          'source_hash': _sha(d / 'A.mm')}],
               'excluded': [{'path': '../Delme.mm', 'reason': 'disposable',
                             'source_hash': _sha(d / 'Delme.mm')}]}
        (d / 'A_old.mm').write_text('diverged')
        (d / 'Delme.mm').write_text('grew content')

        delta = KnowledgebaseIndexer._dir_content_delta(seg, d / '.kb')

        decisions = {e['path']: e['decision'] for e in delta['reopened']}
        assert decisions == {'A_old.mm': "supersedes of card 'a'",
                             'Delme.mm': 'excluded (disposable)'}
        assert delta['changed'] == [] and delta['new'] == []

    def test_card_without_hash_counts_unchanged(self, tmp_path):
        # A hashless card's source is tracked-but-uncomparable — it must not
        # surface as new (which would mark the directory stale forever).
        d = _make_dir(tmp_path, {'A.mm': 'alpha'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.mm'}]}
        delta = KnowledgebaseIndexer._dir_content_delta(seg, d / '.kb')
        assert delta['unchanged'] == 1
        assert KnowledgebaseIndexer._delta_has_drift(delta) is False


@pytest.mark.quick
class TestSourceDiff:
    """Phase 3: best-effort diff embedding (git-recoverable old content)."""

    def _git_repo(self, tmp_path, files):
        _make_dir(tmp_path, files)
        subprocess.run(['git', 'init', '-q', str(tmp_path)],
                       check=True, capture_output=True)
        for k, v in [('user.name', 'T'), ('user.email', 't@e.c')]:
            subprocess.run(['git', '-C', str(tmp_path), 'config', k, v],
                           check=True, capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'add', '.'],
                       check=True, capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-q', '-m', 'v1'],
                       check=True, capture_output=True)
        return tmp_path

    def test_diff_from_git_head(self, tmp_path):
        repo = self._git_repo(tmp_path, {'A.md': 'line1\nline2\n'})
        old_hash = _sha(repo / 'A.md')
        (repo / 'A.md').write_text('line1\nline2 edited\n')
        diff = KnowledgebaseIndexer._source_diff(str(repo), 'A.md', old_hash)
        assert diff is not None
        assert '-line2' in diff and '+line2 edited' in diff

    def test_no_diff_when_head_is_not_carded_version(self, tmp_path):
        repo = self._git_repo(tmp_path, {'A.md': 'line1\n'})
        (repo / 'A.md').write_text('line1\nline2\n')
        # old_hash deliberately not HEAD's hash — base untrusted, no diff
        diff = KnowledgebaseIndexer._source_diff(
            str(repo), 'A.md', 'sha256:' + '0' * 64)
        assert diff is None

    def test_no_diff_outside_git(self, tmp_path):
        d = _make_dir(tmp_path, {'A.md': 'x\n'})
        assert KnowledgebaseIndexer._source_diff(str(d), 'A.md', _sha(d / 'A.md')) is None

    def test_oversized_diff_omitted(self, tmp_path):
        repo = self._git_repo(tmp_path, {'A.md': 'x\n'})
        old_hash = _sha(repo / 'A.md')
        (repo / 'A.md').write_text('\n'.join(f'l{i}' for i in range(500)) + '\n')
        assert KnowledgebaseIndexer._source_diff(str(repo), 'A.md', old_hash) is None

    def test_delta_file_embeds_diff(self, tmp_path):
        repo = self._git_repo(tmp_path, {'A.md': 'line1\nline2\n'})
        seg = {'cards': [{'slug': 'a', 'source': '../A.md',
                          'source_hash': _sha(repo / 'A.md')}]}
        (repo / 'A.md').write_text('line1\nline2 edited\n')
        delta = KnowledgebaseIndexer._dir_content_delta(seg, repo / '.kb')
        gen = KnowledgebaseIndexer({'directories': {'include': []},
                                    'output': {'file': 'x.mm'}})
        out = gen._write_delta_file(tmp_path / 'deltas', str(repo), delta)
        assert out is not None
        doc = yaml.safe_load(Path(out).read_text().split('\n', 1)[1])
        assert doc['unchanged'] == 0
        assert doc['changed'][0]['path'] == 'A.md'
        assert '+line2 edited' in doc['changed'][0]['diff']


@pytest.mark.quick
class TestHelperSubcommands:
    """Phase 3: `kbi hash` and `kbi manifest-sync`."""

    def test_run_hash_output(self, tmp_path, capsys):
        f = tmp_path / 'a.txt'
        f.write_text('alpha')
        assert run_hash([str(f)]) == 0
        out = capsys.readouterr().out.strip()
        assert out == f"{_sha(f)}  {f}"

    def test_run_hash_missing_file(self, tmp_path, capsys):
        assert run_hash([str(tmp_path / 'nope')]) == 2

    def test_manifest_sync_refreshes_everything(self, tmp_path, capsys):
        d = _make_dir(tmp_path, {'A.md': 'alpha', 'B.md': 'beta',
                                 'A_old.md': 'v1', 'Delme.md': 'scratch'})
        seg = {
            'version': 1, 'updated': '2026-06-01', 'density': 'normal',
            'dir_fingerprint': 'sha256:stale',
            'cards': [
                {'slug': 'a', 'file': 'a.kb.md', 'source': '../A.md',
                 'supersedes': [{'path': '../A_old.md', 'source_hash': 'sha256:old'}],
                 'source_hash': 'sha256:old'},
                {'slug': 'b', 'file': 'b.kb.md', 'source': '../B.md',
                 'source_hash': _sha(d / 'B.md')},
                {'slug': 'dir', 'file': 'dir.kb.md', 'kind': 'dir_summary',
                 'source': '..', 'dir_hash': 'sha256:old'},
            ],
            'excluded': [{'path': '../Delme.md', 'reason': 'disposable',
                          'source_hash': 'sha256:old'}],
        }
        seg_path = d / '.kb' / 'segmentation.yml'
        seg_path.write_text(yaml.safe_dump(seg, sort_keys=False))

        assert run_manifest_sync([str(d)]) == 0

        synced = yaml.safe_load(seg_path.read_text())
        cards = {c['slug']: c for c in synced['cards']}
        assert cards['a']['source_hash'] == _sha(d / 'A.md')
        assert cards['a']['supersedes'][0]['source_hash'] == _sha(d / 'A_old.md')
        assert cards['b']['source_hash'] == _sha(d / 'B.md')  # untouched value
        assert synced['excluded'][0]['source_hash'] == _sha(d / 'Delme.md')
        assert cards['dir']['dir_hash'] == _compute_dir_hash(
            [_sha(d / 'A.md'), _sha(d / 'B.md')])
        assert synced['dir_fingerprint'] != 'sha256:stale'
        out = capsys.readouterr().out
        assert 'source_hash updated: 1' in out
        assert 'dir_hash: changed' in out
        # Sync result must read back as content-current (no drift).
        assert KnowledgebaseIndexer._dir_content_changed(synced, d / '.kb') is False

    def test_manifest_sync_no_manifest(self, tmp_path):
        assert run_manifest_sync([str(tmp_path)]) == 2


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
