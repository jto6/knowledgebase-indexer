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
import os
import fnmatch
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
from index_model import file_is_generated
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
    
    def build_file_system_index(self, files: List[str], handlers: Dict[str, Any]) -> Dict[str, List[HierarchicalNode]]:
        """Build hierarchical file system index."""
        file_system_index = {}
        
        for file_path in files:
            handler = handlers.get(file_path)
            if not handler:
                continue
            
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
    
    def process_keyword_searches(self, files: List[str], handlers: Dict[str, Any]) -> List[Any]:
        """Process keyword-based searches and return hierarchical keyword entries with results."""
        keyword_files = self.config.get('keywords', {}).get('files', [])
        
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
    
    def _execute_keyword_searches(self, entries: List, files: List[str], handlers: Dict[str, Any]):
        """Recursively execute searches for keyword entries and store results."""
        for entry in entries:
            if entry.is_leaf:
                # This is a search pattern - execute the search
                if ':' in entry.text:
                    # Multi-term sequence
                    sequence = [term.strip() for term in entry.text.split(':')]
                else:
                    # Single term
                    sequence = [entry.text]
                
                if self.debug:
                    print(f"Searching sequence: {' → '.join(sequence)}")
                
                search_results = self.search_engine.search_sequence(files, sequence, handlers)
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
        from index_model import IndexModel, DomainIndex, resolve_domain, NONE_DOMAIN

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

        model = IndexModel(partitioned=partitioned)
        for name, bfiles in buckets.items():
            di = DomainIndex(name=name, files=bfiles)
            di.file_system = self.build_file_system_index(bfiles, handlers)
            di.keyword_entries = self.process_keyword_searches(bfiles, handlers)
            di.tags = self.extract_tags(bfiles, handlers)
            di.words = self.extract_significant_words(bfiles, handlers)
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate navigational knowledge indexes for structured file collections (Freeplane .mm by default)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate an index from a config file (required)
  python kbi.py configs/Study25.yml

  # Override the output path
  python kbi.py configs/Study25.yml --output my_index.mm

  # Enable debug output and file logging
  python kbi.py configs/Study25.yml --debug --log-file /path/to/debug.log

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
        '--sample-config',
        action='store_true',
        help='Create sample configuration file and exit'
    )
    
    parser.add_argument(
        '--sample-keywords',
        action='store_true',
        help='Create sample keyword file and exit'
    )
    
    args = parser.parse_args()
    
    # Handle sample file generation
    if args.sample_config:
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
  #   word: "off"

# Select which built-in types to index (handlers are built in). Omit `types` to
# index all. A file is classified by its most-specific type (.kb.md = card).
# types:
#   exclude: [card]             # e.g. a deep content index without card summaries
#   include: [card]             # or a card-only catalog
"""
        
        with open('kbi.yml', 'w') as f:
            f.write(sample_config)
        print("Sample configuration file created: kbi.yml")
        return 0
    
    if args.sample_keywords:
        from keywords import create_sample_keyword_file
        create_sample_keyword_file('keywords.txt')
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