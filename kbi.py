#!/usr/bin/env python3
"""
Knowledgebase Indexer - Builds navigational indexes over structured file collections.

This is the main entry point that implements the functionality described in kbi_PRD.md.
It computes a render-independent index model with four navigation views, then emits
it through a renderer (Freeplane .mm mind map by default; a Markdown renderer is
planned). The four views are:
- File System Index: Hierarchical directory structure
- Keyword Index: Context-sensitive search results
- Tag Index: Tag-based file organization
- Word Index: Significant word frequency index
"""

import sys
import argparse
import glob
import hashlib
import os
import fnmatch
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback
import time

# Import our modules
from config import ConfigLoader

# Import from the main handlers module
from core_handlers import handler_registry, HierarchicalNode

from handlers.freeplane_handler import FreeplaneHandler
from handlers.markdown_handler import MarkdownHandler
from handlers.card_handler import CardHandler
from search import HierarchicalSearchEngine, SearchResultAggregator
from keywords import load_keyword_files, KeywordProcessor
from mindmap_generator import FreeplaneMapGenerator
from markdown_renderer import MarkdownIndexRenderer
from index_model import file_is_generated, CardGroup
from handlers.card_handler import is_file_summary, is_dir_summary
from word_filter import SignificantWordFilter
from logging_config import AppLogger, LoggedOperation, create_component_logger


# Built-in file types: (name, extensions, handler). Handlers are part of kbi — the
# config selects among these by name (`types` include/exclude); it never declares
# them. A file is classified by its most-specific (longest-extension) matching type.
BUILTIN_TYPES = [
    ("card", [".kb.md"], "CardHandler"),
    ("freeplane", [".mm"], "FreeplaneHandler"),
    ("markdown", [".md", ".markdown"], "MarkdownHandler"),
]


# Built-in source-exclude patterns applied by --update's staleness check even
# when no kb.yml is present.  Users can extend (not replace) via kb.yml
# `source_exclude`.  Hidden files (.*) are always excluded separately.
_DEFAULT_SOURCE_EXCLUDE = [
    '*.conflict*',   # Google Drive / OneDrive sync-conflict artefacts
    '*.mm.md',       # mm2md converted outputs (derived, not source)
    'CLAUDE.md',     # Claude Code project instructions — never a KB source
]


class KnowledgebaseIndexer:
    """Main application class for generating knowledge indexes (render-independent model, pluggable renderers)."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.debug = False
        self.logger = create_component_logger('main')
        
        # Initialize components
        self.config_loader = ConfigLoader()
        self.search_engine = HierarchicalSearchEngine()
        self.result_aggregator = SearchResultAggregator()
        self.keyword_processor = KeywordProcessor()
        
        # Register handlers
        handler_registry.register_handler('FreeplaneHandler', FreeplaneHandler)
        handler_registry.register_handler('MarkdownHandler', MarkdownHandler)
        handler_registry.register_handler('CardHandler', CardHandler)
        
        self.logger.info("KnowledgebaseIndexer initialized successfully")
    
    def set_debug(self, debug: bool):
        """Enable or disable debug output."""
        self.debug = debug
        self.search_engine.set_debug(debug)
        self.keyword_processor.set_debug(debug)
    
    def _enabled_types(self) -> List[str]:
        """Type names enabled by config `types`: include (whitelist) | exclude
        (blacklist) | neither (all built-in types)."""
        names = [t[0] for t in BUILTIN_TYPES]
        spec = self.config.get('types') or {}
        if spec.get('include') is not None:
            inc = set(spec['include'])
            return [n for n in names if n in inc]
        if spec.get('exclude') is not None:
            exc = set(spec['exclude'])
            return [n for n in names if n not in exc]
        return names

    def _type_of(self, filename: str):
        """The file's type = its most-specific (longest-extension) matching built-in
        type, or None. So `foo.kb.md` is a `card`, not `markdown`."""
        best, best_len = None, -1
        for name, exts, _ in BUILTIN_TYPES:
            for e in exts:
                if filename.endswith(e) and len(e) > best_len:
                    best, best_len = name, len(e)
        return best

    def _builtin_handler(self, type_name: str):
        for name, exts, handler_name in BUILTIN_TYPES:
            if name == type_name:
                return handler_registry.get_handler(handler_name, {'extensions': exts})
        return None

    def discover_files(self) -> List[str]:
        """Discover files in directories matching glob patterns, filtered to enabled built-in types.

        Optimized version that uses os.walk with early directory pruning for much better performance.
        """
        with LoggedOperation('main', 'file_discovery') as op:
            include_dir_patterns = self.config['directories']['include']
            exclude_dir_patterns = self.config['directories'].get('exclude', [])

            # Automatically exclude the output file to prevent self-indexing
            output_file = Path(self.config['output']['file']).resolve()
            self.logger.debug(f"Excluding output file from indexing: {output_file}")

            # Candidate extensions = every built-in type's extensions; a file is
            # kept only if its most-specific type is enabled (config `types`).
            enabled_types = set(self._enabled_types())
            supported_extensions = set()
            for _name, exts, _h in BUILTIN_TYPES:
                supported_extensions.update(exts)

            AppLogger.log_algorithm_step('main', 'starting_file_discovery', {
                'include_dir_patterns': len(include_dir_patterns),
                'exclude_dir_patterns': len(exclude_dir_patterns),
                'supported_extensions': len(supported_extensions)
            })

            self.logger.debug(f"Include directory patterns: {include_dir_patterns}")
            self.logger.debug(f"Exclude directory patterns: {exclude_dir_patterns}")
            self.logger.debug(f"Supported extensions: {sorted(supported_extensions)}")

            # Resolve include directories (simple patterns, not recursive glob)
            include_directories = []
            for pattern in include_dir_patterns:
                path = Path(pattern).expanduser()
                if path.exists():
                    if path.is_dir():
                        include_directories.append(path.resolve())
                    elif path.is_file():
                        include_directories.append(path.parent.resolve())
                else:
                    self.logger.warning(f"Include pattern does not exist: {pattern}")

            self.logger.info(f"Scanning {len(include_directories)} root directories")

            # Helper function to check if a path matches any exclude pattern
            def is_excluded(path_str: str) -> bool:
                """Check if a path matches any exclude pattern."""
                for pattern in exclude_dir_patterns:
                    # Handle ** patterns by converting to fnmatch-style
                    if '**' in pattern:
                        # Extract the directory name to exclude (e.g., "node_modules" from "**/node_modules/**")
                        parts = pattern.strip('*').strip('/').split('/')
                        for part in parts:
                            if part and part in path_str.split(os.sep):
                                return True
                    elif fnmatch.fnmatch(path_str, pattern):
                        return True
                return False

            # Walk directories and collect files with early pruning
            all_files = set()
            dirs_scanned = 0
            dirs_pruned = 0

            for root_directory in include_directories:
                try:
                    for dirpath, dirnames, filenames in os.walk(str(root_directory)):
                        dirs_scanned += 1

                        # Prune excluded directories IN-PLACE to avoid descending into them
                        # This is the key optimization - we never visit excluded dirs
                        dirs_to_remove = []
                        for dirname in dirnames:
                            full_dir_path = os.path.join(dirpath, dirname)
                            if is_excluded(full_dir_path):
                                dirs_to_remove.append(dirname)
                                dirs_pruned += 1

                        for dirname in dirs_to_remove:
                            dirnames.remove(dirname)

                        # Process files in this directory
                        for filename in filenames:
                            file_path = os.path.join(dirpath, filename)

                            # Keep only files whose most-specific built-in type is enabled
                            if (any(filename.endswith(ext) for ext in supported_extensions)
                                    and self._type_of(filename) in enabled_types):
                                # Double-check the full path isn't in an excluded location,
                                # isn't the output file, and isn't a kbi-generated index
                                # (skip our own output anywhere in the tree, not just the
                                # configured output path — avoids self-recursion).
                                if (not is_excluded(file_path)
                                        and Path(file_path).resolve() != output_file
                                        and not file_is_generated(file_path)):
                                    all_files.add(file_path)

                        # Progress logging for large scans
                        if dirs_scanned % 1000 == 0:
                            self.logger.debug(f"Scanned {dirs_scanned} directories, pruned {dirs_pruned}, found {len(all_files)} files so far...")

                except PermissionError:
                    self.logger.warning(f"Permission denied accessing directory: {root_directory}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error scanning directory {root_directory}: {e}")
                    continue

            # Convert to sorted list
            result_files = sorted(list(all_files))

            AppLogger.log_algorithm_step('main', 'file_discovery_complete', {
                'include_dirs': len(include_directories),
                'dirs_scanned': dirs_scanned,
                'dirs_pruned': dirs_pruned,
                'files_found': len(result_files)
            })

            self.logger.info(f"File discovery complete: {len(result_files)} files found (scanned {dirs_scanned} dirs, pruned {dirs_pruned})")

            return result_files
    
    def create_file_handlers(self, files: List[str]) -> Dict[str, Any]:
        """Assign each file the handler for its (enabled) built-in type."""
        handlers = {}
        enabled_types = set(self._enabled_types())
        for file_path in files:
            t = self._type_of(file_path)
            if t not in enabled_types:
                continue
            handler = self._builtin_handler(t)
            if handler and handler.validate_file(file_path):
                handlers[file_path] = handler
            elif self.debug:
                print(f"No handler found for: {file_path}")
        
        if self.debug:
            print(f"Created handlers for {len(handlers)} files")
        
        return handlers
    
    def build_file_system_index(self, files: List[str], handlers: Dict[str, Any],
                               exported_paths: Optional[set] = None) -> Dict[str, List[HierarchicalNode]]:
        """Build hierarchical file system index for non-card files.

        Card files are excluded here — they appear in `build_card_groups` instead,
        grouped under their source path with FS-view annotations (D21).

        `exported_paths` is the set of absolute paths that are format-export
        derivatives (e.g. a .pdf exported from a .pptx). They carry no independent
        content and are suppressed from the FS view.
        """
        file_system_index = {}
        skip = exported_paths or set()

        for file_path in files:
            handler = handlers.get(file_path)
            if not handler:
                continue
            if isinstance(handler, CardHandler):
                continue  # cards go through build_card_groups
            if file_path in skip:
                continue  # format-export derivative — absorbed by its source card group

            try:
                root_nodes = handler.get_root_nodes(file_path)
                file_system_index[file_path] = root_nodes

                if self.debug:
                    print(f"Indexed {file_path}: {len(root_nodes)} root nodes")

            except Exception as e:
                if self.debug:
                    print(f"Error indexing {file_path}: {e}")
                continue

        return file_system_index

    @staticmethod
    def _resolve_path_list(card_record: Dict[str, Any], field: str) -> List[str]:
        """Resolve a frontmatter list field of relative paths to absolute paths.

        Used for `exported_as` and `refines`. Returns a (possibly empty) list;
        URL entries are silently dropped.
        """
        file_path = card_record.get('file_path', '')
        raw = card_record.get(field) or []
        if isinstance(raw, str):
            raw = [raw]
        card_dir = Path(file_path).parent
        result = []
        for entry in raw:
            s = str(entry).strip()
            if not s or s.startswith(('http://', 'https://')):
                continue
            result.append(str((card_dir / s).resolve()))
        return result

    @staticmethod
    def _resolve_exported_as(card_record: Dict[str, Any]) -> List[str]:
        """Resolve the `exported_as` frontmatter list to absolute filesystem paths."""
        return KnowledgebaseIndexer._resolve_path_list(card_record, 'exported_as')

    @staticmethod
    def _resolve_refines(card_record: Dict[str, Any]) -> List[str]:
        """Resolve the `refines` frontmatter list to absolute filesystem paths.

        `refines` lists the superseded/absorbed source files that were folded into
        this canonical card. Those files carry no independent content and are
        suppressed from the FS view.
        """
        return KnowledgebaseIndexer._resolve_path_list(card_record, 'refines')

    @staticmethod
    def _parse_md_link_path(s: str) -> str:
        """Extract the path from a markdown link '[text](<path>)' or '[text](path)'.

        Returns the path portion, or `s` unchanged if it is not a markdown link.
        Angle-bracket form '[text](<path with spaces>)' is used when the path
        contains spaces (CommonMark spec); both forms are accepted here.
        """
        m = re.match(r'^\[([^\]]*)\]\(<([^>]*)>\)$', s)
        if m:
            return m.group(2)
        m = re.match(r'^\[([^\]]*)\]\(([^)]*)\)$', s)
        if m:
            return m.group(2)
        return s

    @staticmethod
    def _resolve_card_source(card_record: Dict[str, Any]) -> Optional[str]:
        """Resolve a card's `source` frontmatter to an absolute filesystem path.

        Returns None for pure-URL sources (no local path). A list source (URL +
        local capture) uses the first non-URL entry as the local path.
        Accepts paths written as markdown links ('[label](path)' or
        '[label](<path with spaces>)') and strips the link syntax.
        """
        file_path = card_record.get('file_path', '')
        source = card_record.get('source')
        if not source:
            return None
        if isinstance(source, list):
            local = next(
                (str(s).strip() for s in source
                 if not str(s).strip().startswith(('http://', 'https://'))),
                None
            )
            if local is None:
                return None
            source = local
        source = KnowledgebaseIndexer._parse_md_link_path(str(source).strip())
        if source.startswith(('http://', 'https://')):
            return None
        card_dir = Path(file_path).parent
        return str((card_dir / source).resolve())

    def build_card_groups(self, bfiles: List[str], card_records: Dict[str, Any]) -> Dict[str, CardGroup]:
        """Group card files by resolved source path and compute FS-view annotations.

        Implements the annotation rule from D21 / REFERENCE.md §1.7 / §5.3:
        - A `kind: file_summary` card → its essence annotates the source node
          and it is NOT rendered as a leaf (hide_summary_card=True).
        - A lone topic card (N=1, no file_summary) → its essence annotates the
          source node; the card IS still rendered as a leaf.
        - N≥2 topic cards with no file_summary → source node has no annotation.
        """
        groups: Dict[str, CardGroup] = {}

        for fp in bfiles:
            rec = card_records.get(fp)
            if not rec:
                continue
            if is_dir_summary(rec):
                continue  # dir_summary cards annotate directory nodes, not file groups
            source = self._resolve_card_source(rec)
            if source is None:
                source = str(Path(fp).parent.parent.resolve())
            if source not in groups:
                groups[source] = CardGroup()
            label = rec.get('title') or Path(fp).name
            groups[source].cards.append((label, fp, rec.get('essence') or ''))
            for exp_path in self._resolve_exported_as(rec):
                if exp_path not in groups[source].exported_as:
                    groups[source].exported_as.append(exp_path)
            for ref_path in self._resolve_refines(rec):
                if ref_path not in groups[source].refines:
                    groups[source].refines.append(ref_path)

        for source, group in groups.items():
            card_recs = [(fp, card_records[fp]) for _, fp, _ in group.cards if fp in card_records]
            summary = [(fp, r) for fp, r in card_recs if is_file_summary(r)]
            topic = [(fp, r) for fp, r in card_recs if not is_file_summary(r)]

            if summary and topic:
                # file_summary exists alongside topic cards: hide the file_summary,
                # use its essence to annotate the source node
                fp, rec = summary[0]
                group.annotation = rec.get('essence', '')
                group.hidden_card = fp
            elif summary and not topic:
                # file_summary is the only card (no topic cards): show it as a leaf
                # (graceful fallback — spec says file_summary meaningful only with N≥2 topics)
                _, rec = summary[0]
                group.annotation = rec.get('essence', '')
                group.hidden_card = None
            elif len(topic) == 1:
                _, rec = topic[0]
                group.annotation = rec.get('essence', '')
                group.hidden_card = None

        return groups

    def build_dir_annotations(self, bfiles: List[str], card_records: Dict[str, Any]) -> Dict[str, str]:
        """Build abs_dir_path → essence mapping from kind: dir_summary cards."""
        dir_annotations: Dict[str, str] = {}
        for fp in bfiles:
            rec = card_records.get(fp)
            if not rec or not is_dir_summary(rec):
                continue
            dir_path = self._resolve_card_source(rec)
            if dir_path is None:
                dir_path = str(Path(fp).parent.parent.resolve())
            essence = rec.get('essence', '')
            if essence:
                dir_annotations[dir_path] = essence
        return dir_annotations

    @staticmethod
    def _compute_dir_fingerprint(directory: str) -> str:
        """SHA-256 hash of sorted {filename,size,mtime_ns} for non-hidden files outside .kb/."""
        entries = []
        try:
            for name in sorted(os.listdir(directory)):
                if name.startswith('.'):
                    continue
                full = os.path.join(directory, name)
                if os.path.isfile(full):
                    st = os.stat(full)
                    entries.append(f"{name},{st.st_size},{st.st_mtime_ns}\n")
        except OSError:
            pass
        digest = hashlib.sha256("".join(entries).encode()).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def _load_source_exclude(source_dir: Path) -> List[str]:
        """Return the source-exclude glob patterns for source_dir.

        Starts with _DEFAULT_SOURCE_EXCLUDE, then appends any patterns from
        the nearest ancestor `.kb/kb.yml` `source_exclude` list.  Nearest-
        ancestor-wins for the yaml key itself; the built-in defaults always
        apply so existing kb.yml files without `source_exclude` still get the
        standard artefact filters.
        """
        patterns: List[str] = list(_DEFAULT_SOURCE_EXCLUDE)
        current = source_dir
        while True:
            kb_yml = current / '.kb' / 'kb.yml'
            if kb_yml.exists():
                try:
                    import yaml as _yaml
                    kb = _yaml.safe_load(kb_yml.read_text(encoding='utf-8')) or {}
                    user = kb.get('source_exclude') or []
                    patterns.extend(user)
                except Exception:
                    pass
                break
            parent = current.parent
            if parent == current:
                break
            current = parent
        return patterns

    @staticmethod
    def _dir_content_changed(seg: Dict[str, Any], kb_dir: Path) -> bool:
        """Return True if any source file referenced in segmentation.yml has changed content.

        Compares each card's stored `source_hash` against a freshly computed
        SHA-256 of that file's bytes.  Files that have been added or removed
        also count as changed.  Pure-URL sources and dir_summary cards (whose
        source is the directory itself, tracked via `dir_hash` not `source_hash`)
        are skipped.

        This is a content-level check that avoids false positives from mtime
        changes (git checkout, sync, touch) that trick the mtime-based
        dir_fingerprint into reporting stale when nothing actually changed.
        """
        source_dir = kb_dir.parent
        cards = seg.get('cards', []) or []
        if not cards:
            # No cards recorded yet — treat as changed so /kb-card can initialise
            return True

        seen_sources: set = set()
        for card in cards:
            # dir_summary cards use dir_hash, not source_hash; their source is
            # the directory itself ('..' relative to .kb/).  Skip them here.
            if card.get('kind') == 'dir_summary':
                continue
            # Also skip any card without a source_hash (no content to compare)
            stored_hash = card.get('source_hash', '')
            if not stored_hash:
                continue

            raw_source = card.get('source', '')
            if not raw_source:
                continue
            # Resolve a list source (URL + local path) to the local path entry
            if isinstance(raw_source, list):
                local = next(
                    (s for s in raw_source if not str(s).startswith('http')),
                    None,
                )
                if local is None:
                    continue
                raw_source = str(local)
            path_str = KnowledgebaseIndexer._parse_md_link_path(str(raw_source).strip())
            if path_str.startswith('http'):
                continue
            source_path = (kb_dir / path_str).resolve()
            if source_path in seen_sources:
                continue
            seen_sources.add(source_path)

            if not source_path.exists():
                return True  # source file deleted
            if source_path.is_dir():
                continue  # safety guard — should not happen for non-dir_summary cards
            try:
                full_hash = 'sha256:' + hashlib.sha256(source_path.read_bytes()).hexdigest()
            except OSError:
                return True
            # stored_hash may be a truncated prefix (e.g. 'sha256:5ca9f4a552e44df8').
            # Compare only as many characters as were stored.
            if not full_hash.startswith(stored_hash):
                return True

        # Check for new source files that have no card yet.  Two filters keep
        # noise out:
        #   1. source_exclude patterns (kb.yml + built-in defaults) — removes
        #      explicitly unwanted files regardless of extension.
        #   2. Extension heuristic — only consider files whose suffix matches
        #      an extension already tracked; this automatically excludes
        #      .pdf/.html/.log/.csv etc. from directories that only track .mm
        #      or .md sources.  Users add same-extension exclusions (e.g.
        #      CLAUDE.md) via kb.yml source_exclude.
        tracked_exts = {p.suffix.lower() for p in seen_sources if p.suffix}
        if tracked_exts:
            exclude_patterns = KnowledgebaseIndexer._load_source_exclude(source_dir)
            try:
                for name in os.listdir(str(source_dir)):
                    if name.startswith('.'):
                        continue
                    if any(fnmatch.fnmatch(name, pat) for pat in exclude_patterns):
                        continue
                    candidate = (source_dir / name).resolve()
                    if not candidate.is_file():
                        continue
                    if candidate.suffix.lower() not in tracked_exts:
                        continue
                    if candidate not in seen_sources:
                        return True
            except OSError:
                pass

        return False

    def _scan_managed_directories(self, config: Dict[str, Any]) -> tuple:
        """Return (stale_dirs, current_count) for all managed directories.

        A managed directory is any directory with a `.kb/segmentation.yml`
        that contains a `dir_fingerprint` field.  Returns a 2-tuple:
          stale_dirs   — list of absolute path strings whose fingerprint
                         no longer matches the stored value
          current_count — count of directories whose fingerprint matches

        Uses a two-level check:
          1. mtime-based dir_fingerprint (fast) — if unchanged, skip immediately.
          2. Content-based source_hash comparison — if dir_fingerprint changed but
             all source file contents are identical to their stored hashes, the
             directory is mtime-stale but content-current; skip Claude.
        """
        try:
            import yaml as _yaml
        except ImportError:
            print("Warning: PyYAML not available", file=sys.stderr)
            return [], 0

        include_dirs = (config.get('directories', {}) or {}).get('include', ['.'])
        if not include_dirs:
            include_dirs = ['.']

        visited: set = set()
        stale: list = []
        current_count = 0

        for inc in include_dirs:
            inc_path = Path(inc).resolve()
            for root, dirs, _files in os.walk(str(inc_path)):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
                seg_yml = Path(root) / '.kb' / 'segmentation.yml'
                try:
                    exists = seg_yml.exists()
                except PermissionError:
                    continue
                if not exists:
                    continue
                abs_dir = str(Path(root).resolve())
                if abs_dir in visited:
                    continue
                visited.add(abs_dir)
                try:
                    seg = _yaml.safe_load(seg_yml.read_text(encoding='utf-8')) or {}
                except Exception:
                    seg = {}
                stored_fp = seg.get('dir_fingerprint', '')
                current_fp = self._compute_dir_fingerprint(abs_dir)
                if current_fp == stored_fp:
                    current_count += 1
                    continue
                # dir_fingerprint changed — do a content-level check before
                # paying the Claude invocation cost.
                if not self._dir_content_changed(seg, seg_yml.parent):
                    current_count += 1
                else:
                    stale.append(abs_dir)

        return stale, current_count

    def run_update(self, config: Dict[str, Any]) -> None:
        """Refresh stale card sets before indexing.

        For every directory under the include paths that has a
        `.kb/segmentation.yml` with a `dir_fingerprint` field, recompute
        the fingerprint and invoke `claude -p /kb-card <dir>` when stale.
        Directories without a `segmentation.yml` are skipped entirely.
        """
        print("--update: scanning for managed directories …", flush=True)
        stale, current_count = self._scan_managed_directories(config)

        for d in stale:
            print(f"  stale: {d}", flush=True)

        total = len(stale) + current_count
        print(f"--update: {total} managed director{'ies' if total != 1 else 'y'} found, "
              f"{len(stale)} stale, {current_count} current", flush=True)

        if not stale:
            return

        for i, d in enumerate(stale, 1):
            print(f"--update: [{i}/{len(stale)}] refreshing {d}", flush=True)
            rc = subprocess.run(['claude', '-p', '/kb-card'], cwd=d).returncode
            if rc != 0:
                print(f"Warning: /kb-card returned {rc} for {d}", file=sys.stderr)

        print(f"--update: done ({len(stale)} director{'ies' if len(stale) != 1 else 'y'} refreshed)", flush=True)

    def _resolve_keyword_files(self, domain: Optional[str]) -> List[str]:
        """Return the keyword file paths that apply to `domain`.

        Each entry in `keywords.files` is either a plain string (global — applies
        to all domains) or a dict ``{path: ..., domain: ...}`` (domain-scoped).
        The `domain` value may be a single string or a list of strings; the file
        is included when `domain` matches any entry in that list.
        For the unpartitioned case (domain is None) all files are included.
        For a named domain, global files and matching domain-scoped files are included.
        For NONE_DOMAIN (files with no domain in a partitioned index) only
        global files are included.
        """
        from index_model import NONE_DOMAIN
        raw = self.config.get('keywords', {}).get('files', [])
        result = []
        for entry in raw:
            if isinstance(entry, str):
                result.append(entry)          # global
            elif isinstance(entry, dict):
                path = entry.get('path', '')
                file_domain = entry.get('domain')
                if file_domain is None:
                    result.append(path)        # global dict form
                elif domain is None:
                    result.append(path)        # unpartitioned: include all
                elif domain != NONE_DOMAIN:
                    domains = [file_domain] if isinstance(file_domain, str) else list(file_domain)
                    if domain in domains:
                        result.append(path)    # domain-scoped match
        return result

    def process_keyword_searches(self, files: List[str], handlers: Dict[str, Any],
                                 domain: Optional[str] = None) -> List[Any]:
        """Process keyword-based searches and return hierarchical keyword entries with results.

        `domain` is the current partition's domain name (None = unpartitioned,
        NONE_DOMAIN = files with no domain). Only keyword files that apply to
        this domain are loaded (see `_resolve_keyword_files`).
        """
        keyword_files = self._resolve_keyword_files(domain)

        if not keyword_files:
            if self.debug:
                print("No keyword files configured")
            return []

        # Load keyword entries
        try:
            keyword_entries, warnings = load_keyword_files(keyword_files, debug=self.debug)
            
            if warnings and self.debug:
                print("Keyword file warnings:")
                for warning in warnings:
                    print(f"  {warning}")
            
            if not keyword_entries:
                if self.debug:
                    print("No keyword entries found")
                return []
            
            # Execute searches for each keyword entry (recursively for the tree)
            self._execute_keyword_searches(keyword_entries, files, handlers)
            
            return keyword_entries
        
        except Exception as e:
            if self.debug:
                print(f"Error processing keywords: {e}")
                traceback.print_exc()
            return []
    
    @staticmethod
    def _split_keyword_sequence(text: str) -> List[str]:
        """Split on ':' that are outside character classes [...].

        A bare ':' is the sequence separator; ':' inside [...] is part of the
        regex pattern and must not be split on.
        """
        parts = []
        current: List[str] = []
        depth = 0
        for ch in text:
            if ch == '[':
                depth += 1
                current.append(ch)
            elif ch == ']' and depth:
                depth -= 1
                current.append(ch)
            elif ch == ':' and not depth:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
        parts.append(''.join(current).strip())
        return parts

    def _execute_keyword_searches(self, entries: List, files: List[str], handlers: Dict[str, Any]):
        """Recursively execute searches for keyword entries and store results."""
        for entry in entries:
            if entry.is_leaf:
                # This is a search pattern - execute the search
                sequence = self._split_keyword_sequence(entry.text)

                if self.debug:
                    print(f"Searching sequence: {' → '.join(sequence)}")

                try:
                    search_results = self.search_engine.search_sequence(files, sequence, handlers)
                except Exception as e:
                    if self.debug:
                        print(f"  Skipping entry {entry.text!r}: {e}")
                    search_results = {}
                # Store results directly on the entry object
                entry.search_results = search_results
            else:
                # This is an interior node - no search, but process children
                entry.search_results = {}
                self._execute_keyword_searches(entry.children, files, handlers)
    
    def extract_tags(self, files: List[str], handlers: Dict[str, Any]) -> Dict[str, List[tuple]]:
        """Extract tags from all files and aggregate by tag (R-TAG-001 to R-TAG-004)."""
        all_tag_results = {}
        
        for file_path in files:
            handler = handlers.get(file_path)
            if not handler:
                continue
            
            try:
                file_tag_map = handler.extract_tags(file_path)
                
                # Merge this file's tag map into the global tag map
                for tag, node_matches in file_tag_map.items():
                    if tag not in all_tag_results:
                        all_tag_results[tag] = []
                    all_tag_results[tag].extend(node_matches)
                    
                if file_tag_map and self.debug:
                    print(f"Extracted tags from {file_path}: {list(file_tag_map.keys())}")
            
            except Exception as e:
                if self.debug:
                    print(f"Error extracting tags from {file_path}: {e}")
                continue
        
        return all_tag_results
    
    def extract_significant_words(self, files: List[str], handlers: Dict[str, Any]) -> Dict[str, Dict]:
        """Extract significant words with match instances (R-WORD-012, R-WORD-013, R-WORD-014, R-WORD-015)."""
        word_filter = SignificantWordFilter()
        word_to_matches = {}
        
        # Get minimum frequency from config, default to 2
        min_frequency = self.config.get('word_index', {}).get('min_frequency', 2)
        
        for file_path in files:
            handler = handlers.get(file_path)
            if not handler:
                continue
            
            try:
                # Get root nodes from handler
                root_nodes = handler.get_root_nodes(file_path)
                
                # Collect word matches from each node
                def collect_word_matches_recursive(node):
                    node_content = handler.get_node_content(node)
                    if node_content:
                        # Extract significant words from this node
                        significant_words = word_filter.extract_significant_words(node_content)
                        
                        # Record matches for each word
                        for word in significant_words:
                            if word not in word_to_matches:
                                word_to_matches[word] = {}
                            if file_path not in word_to_matches[word]:
                                word_to_matches[word][file_path] = []
                            
                            # Create match instance
                            match_instance = {
                                'node_id': getattr(node, 'id', ''),
                                'node_text': getattr(node, 'text', ''),
                                'node_type': getattr(node, 'node_type', 'content'),
                                'file_path': file_path
                            }
                            
                            # Avoid duplicates
                            if match_instance not in word_to_matches[word][file_path]:
                                word_to_matches[word][file_path].append(match_instance)
                    
                    # Recurse through children
                    for child in handler.get_child_nodes(node):
                        collect_word_matches_recursive(child)
                
                for root_node in root_nodes:
                    collect_word_matches_recursive(root_node)
                
                if self.debug:
                    word_count = sum(len(matches) for matches in word_to_matches.values() 
                                   if file_path in matches)
                    if word_count > 0:
                        print(f"Extracted word matches from {file_path}: {word_count} match instances")
                
            except Exception as e:
                if self.debug:
                    print(f"Error extracting words from {file_path}: {e}")
                continue
        
        # Filter by minimum frequency (R-WORD-005)
        filtered_words = {}
        for word, file_matches in word_to_matches.items():
            total_files = len(file_matches)
            if total_files >= min_frequency:
                filtered_words[word] = file_matches
        
        # Apply word consolidation (R-WORD-014, R-WORD-015)
        word_to_files_simple = {word: list(matches.keys()) for word, matches in filtered_words.items()}
        consolidated = word_filter.consolidate_word_variations(word_to_files_simple, max_combined=24)
        
        # Convert back to match-instance format
        consolidated_matches = {}
        for pattern, consolidation_info in consolidated.items():
            if consolidation_info['is_consolidated']:
                # Merge matches from all consolidated words
                merged_matches = {}
                for original_word in consolidation_info['words']:
                    if original_word in filtered_words:
                        for file_path, match_instances in filtered_words[original_word].items():
                            if file_path not in merged_matches:
                                merged_matches[file_path] = []
                            merged_matches[file_path].extend(match_instances)
                consolidated_matches[pattern] = merged_matches
            else:
                # Use original word if available in filtered_words
                original_word = consolidation_info['words'][0]
                if original_word in filtered_words:
                    consolidated_matches[pattern] = filtered_words[original_word]
        
        if self.debug:
            print(f"Consolidated {len(word_to_matches)} words into {len(consolidated_matches)} patterns with frequency >= {min_frequency}")
        
        return consolidated_matches

    def build_index_model(self, files: List[str], handlers: Dict[str, Any]):
        """Build the unified, domain-partitioned index model (D16).

        Resolves each file's domain (card frontmatter → nearest kb.yml → none),
        partitions files by domain (a single unpartitioned bucket when no file has
        a domain), and computes every view per partition. Card-only views
        (dependencies, glossary) are populated from card records.
        """
        from index_model import (IndexModel, DomainIndex, resolve_domain,
                                  NONE_DOMAIN, view_enabled, VIEW_WORD)

        # The word index is opt-in and expensive (tokenises every node of every
        # file). Skip computing it entirely unless it will be emitted, so disabling
        # it saves the build time, not just the output size.
        renderer = (self.config.get('output', {}) or {}).get('format', 'freeplane')
        word_on = view_enabled(self.config, VIEW_WORD, renderer)

        card_records: Dict[str, Dict[str, Any]] = {}
        file_domain: Dict[str, Any] = {}
        any_domain = False
        for fp in files:
            handler = handlers.get(fp)
            rec = None
            if isinstance(handler, CardHandler):
                try:
                    rec = handler.get_card_record(fp)
                    card_records[fp] = rec
                except Exception as e:
                    if self.debug:
                        print(f"Error reading card {fp}: {e}")
            dom = resolve_domain(fp, rec)
            if dom:
                any_domain = True
            file_domain[fp] = dom

        # Whether to partition by domain: auto (partition iff any file has a
        # domain) | on (always) | off (never — a single flat index).
        setting = (self.config.get('output', {}) or {}).get('partition_by_domain', 'auto')
        partitioned = True if setting == 'on' else False if setting == 'off' else any_domain

        def bucket(dom):
            if not partitioned:
                return None
            return dom if dom else NONE_DOMAIN

        buckets: Dict[Any, List[str]] = {}
        for fp in files:
            buckets.setdefault(bucket(file_domain[fp]), []).append(fp)

        # slug/id → record, for cross-domain dependency resolution
        card_by_key: Dict[str, Dict[str, Any]] = {}
        for rec in card_records.values():
            if rec.get('slug'):
                card_by_key[str(rec['slug'])] = rec
            if rec.get('id'):
                card_by_key[str(rec['id'])] = rec

        # Pre-compute the set of all absorbed paths (format-export derivatives and
        # superseded/refined sources) so they can be suppressed from the FS view.
        all_exported: set = set()
        for rec in card_records.values():
            all_exported.update(self._resolve_exported_as(rec))
            all_exported.update(self._resolve_refines(rec))

        model = IndexModel(partitioned=partitioned)
        for name, bfiles in buckets.items():
            di = DomainIndex(name=name, files=bfiles)
            di.file_system = self.build_file_system_index(bfiles, handlers, all_exported)
            di.card_groups = self.build_card_groups(bfiles, card_records)
            di.dir_annotations = self.build_dir_annotations(bfiles, card_records)
            di.keyword_entries = self.process_keyword_searches(bfiles, handlers, domain=name)
            di.tags = self.extract_tags(bfiles, handlers)
            di.words = self.extract_significant_words(bfiles, handlers) if word_on else {}
            for fp in bfiles:
                rec = card_records.get(fp)
                if not rec:
                    continue
                for term in (rec.get('defines') or []):
                    di.glossary[str(term)] = rec
                deps = rec.get('builds_on') or []
                if deps:
                    targets = [(card_by_key[str(r)]['title'] if str(r) in card_by_key else str(r),
                                card_by_key.get(str(r), {}).get('file_path'))
                               for r in deps]
                    di.dependencies.append((rec, targets))
            model.domains[name] = di
        return model

    def run(self) -> str:
        """Discover files, build the unified model, and render it.

        `output.format` selects only the renderer; the model is always the full
        superset (D16).
        """
        try:
            if self.debug:
                print("=== Index Generation Process ===")
            files = self.discover_files()
            if not files:
                raise ValueError("No files found matching the configured patterns")
            handlers = self.create_file_handlers(files)
            if not handlers:
                raise ValueError("No valid handlers found for discovered files")
            valid_files = list(handlers.keys())

            if self.debug:
                print("\n=== Building Index Model ===")
            model = self.build_index_model(valid_files, handlers)

            output_format = self.config['output'].get('format', 'freeplane')
            if self.debug:
                print(f"\n=== Rendering ({output_format}) ===")
            if output_format == 'markdown':
                return MarkdownIndexRenderer(self.config).render_model(model)
            generator = FreeplaneMapGenerator(self.config['output']['file'])
            return generator.render_model(model, self.config)

        except Exception as e:
            if self.debug:
                print(f"Error during index generation: {e}")
                traceback.print_exc()
            raise


def _apply_output_default(config: dict, config_path: str) -> None:
    """Set output.file from the config stem when not explicitly configured."""
    if config['output'].get('file'):
        return
    stem = Path(config_path).stem
    fmt = config['output'].get('format', 'freeplane')
    config['output']['file'] = f"{stem}.mm" if fmt == 'freeplane' else stem


def run_search(argv: List[str]) -> int:
    """`kbi search <config> PATTERN [backend args]` — search the indexed files.

    Discovers exactly the files the index would cover (same `types`, directory
    excludes, and generated-file skip), then runs ripgrep (preferred) or grep over
    that file set. Arguments after PATTERN are passed through to the backend.
    """
    import shutil
    import subprocess

    parser = argparse.ArgumentParser(
        prog='kbi search',
        description="Search the files an index config covers, using ripgrep (or grep).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Extra arguments after PATTERN are passed through to the backend (rg, else grep):
  kbi search configs/Study25.yml "a-core" -i -C2
  kbi search configs/Study25.yml "TODO" -l        # list matching files only
        """
    )
    parser.add_argument('config', help='Path to the index configuration file')
    parser.add_argument('pattern', help='Search pattern (regex)')
    args, passthrough = parser.parse_known_args(argv)

    try:
        config = ConfigLoader().load_config(args.config)
        _apply_output_default(config, args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    files = KnowledgebaseIndexer(config).discover_files()
    if not files:
        print("No indexed files to search (check the config's directories/types).",
              file=sys.stderr)
        return 1

    backend = shutil.which('rg') or shutil.which('grep')
    if not backend:
        print("Error: neither `rg` nor `grep` is on PATH.", file=sys.stderr)
        return 2
    is_rg = os.path.basename(backend) == 'rg'

    # grep needs filename+line-number forced on; rg shows both by default.
    base = [backend] if is_rg else [backend, '-n', '-H']
    base += [*passthrough, '-e', args.pattern, '--']

    # Search in chunks to stay under ARG_MAX; aggregate the exit status the way
    # rg/grep do: 0 = match found, 1 = no match, >1 = error.
    CHUNK = 2000
    found = error = False
    for i in range(0, len(files), CHUNK):
        rc = subprocess.run(base + files[i:i + CHUNK]).returncode
        if rc == 0:
            found = True
        elif rc > 1:
            error = True
    return 2 if error else (0 if found else 1)


def main():
    """Main entry point."""
    argv = sys.argv[1:]
    if argv and argv[0] == 'search':
        return run_search(argv[1:])

    parser = argparse.ArgumentParser(
        description="Generate navigational knowledge indexes for structured file collections (Freeplane .mm by default)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate an index from a config file (required)
  python kbi.py configs/Study25.yml

  # Override the output path
  python kbi.py configs/Study25.yml --output my_index.mm

  # Search just the indexed files (ripgrep, else grep)
  python kbi.py search configs/Study25.yml "a-core" -i

  # Scaffold a starter config (writes kbi.yml and exits; no config needed)
  python kbi.py --sample-config
        """
    )

    parser.add_argument(
        'config',
        nargs='?',
        help='Path to configuration file (required, except with --sample-config/--sample-keywords)'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output file path (overrides config)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug output'
    )
    
    parser.add_argument(
        '--log-file',
        help='Path to debug log file (default: auto-generated in /tmp)'
    )
    
    parser.add_argument(
        '--console-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='WARNING',
        help='Console logging level (default: WARNING)'
    )
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='Refresh stale card sets (via claude -p /kb-card) before indexing'
    )

    parser.add_argument(
        '--sample-config',
        nargs='?', const='kbi.yml', default=None, metavar='PATH',
        help='Write a sample configuration file (default: kbi.yml) and exit'
    )

    parser.add_argument(
        '--sample-keywords',
        nargs='?', const='keywords.txt', default=None, metavar='PATH',
        help='Write a sample keyword file (default: keywords.txt) and exit'
    )
    
    args = parser.parse_args()
    
    # Handle sample file generation
    if args.sample_config is not None:
        sample_config = """# Sample kbi configuration file
directories:
  include:
    - "src/"
    - "docs/"
    - "."
  exclude:
    - "**/node_modules/**"
    - "**/.git/**"
    - "**/build/**"
    - "**/__pycache__/**"
    - "**/.venv/**"

keywords:
  files:
    - "keywords.txt"

output:
  file: "index.mm"
  format: "freeplane"
  partition_by_domain: "auto"   # auto | on | off
  # views:                      # per-view emission override (auto|on|off)
  #   word: "on"                # the word index is opt-in (off by default); use
  #                             # `kbi search <config> PATTERN` for ad-hoc lookups

# Select which built-in types to index (handlers are built in). Omit `types` to
# index all. A file is classified by its most-specific type (.kb.md = card).
# types:
#   exclude: [card]             # e.g. a deep content index without card summaries
#   include: [card]             # or a card-only catalog
"""
        
        dest = Path(args.sample_config)
        if dest.parent != Path('.'):
            dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(sample_config)
        print(f"Sample configuration file created: {dest}")
        return 0

    if args.sample_keywords is not None:
        from keywords import create_sample_keyword_file
        dest = Path(args.sample_keywords)
        if dest.parent != Path('.'):
            dest.parent.mkdir(parents=True, exist_ok=True)
        create_sample_keyword_file(str(dest))
        return 0

    # A config is required for any actual indexing run (the utility modes above
    # exit before reaching here).
    if not args.config:
        parser.error("a config file is required (e.g. `kbi.py configs/Study25.yml`); "
                     "use --sample-config to scaffold one")

    try:
        # Set up logging first
        console_level = 'DEBUG' if args.debug else args.console_level
        log_file_path = AppLogger.setup_logging(
            console_level=console_level,
            enable_file_logging=True,
            log_file=args.log_file
        )
        
        main_logger = create_component_logger('startup')
        main_logger.info("Starting Knowledgebase Indexer")
        
        if log_file_path:
            main_logger.info(f"Debug logging enabled - Log file: {log_file_path}")
        
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(args.config)
        _apply_output_default(config, args.config)

        main_logger.info(f"Configuration loaded from: {args.config}")

        # Override output if specified
        if args.output:
            config['output']['file'] = args.output
            main_logger.info(f"Output file overridden: {args.output}")
        
        # Create and run generator
        with LoggedOperation('startup', 'full_index_generation',
                           {'output_file': config['output']['file']}) as op:
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(args.debug)

            if args.update:
                generator.run_update(config)

            output_path = generator.run()
        
        main_logger.info(f"Index generation completed successfully: {output_path}")
        print(f"Index generated: {output_path}")
        
        if args.debug and log_file_path:
            print(f"Debug log available at: {log_file_path}")
        
        return 0
    
    except Exception as e:
        # Log error with context
        error_logger = create_component_logger('error')
        AppLogger.log_error_context('error', e, {
            'config_file': args.config,
            'output_file': args.output,
            'debug_mode': args.debug
        }, 'main_execution')
        
        print(f"Error: {e}", file=sys.stderr)
        
        if args.debug:
            traceback.print_exc()
        
        if args.debug:
            log_file = AppLogger.get_log_file_path()
            if log_file:
                print(f"Full debug information available in: {log_file}", file=sys.stderr)
        
        return 1


if __name__ == '__main__':
    sys.exit(main())