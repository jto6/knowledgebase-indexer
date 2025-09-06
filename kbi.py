#!/usr/bin/env python3
"""
Knowledgebase Indexer - Creates navigational mind map indexes for structured file collections.

This is the main entry point that implements the functionality described in mmdir_PRD.md.
It generates Freeplane-compatible mind maps with three navigation views:
- File System Index: Hierarchical directory structure
- Keyword Index: Context-sensitive search results
- Tag Index: Tag-based file organization
"""

import sys
import argparse
import glob
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
from search import HierarchicalSearchEngine, SearchResultAggregator
from keywords import load_keyword_files, KeywordProcessor
from mindmap_generator import FreeplaneMapGenerator
from logging_config import AppLogger, LoggedOperation, create_component_logger


class KnowledgebaseIndexer:
    """Main application class for generating mind map indexes."""
    
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
        
        self.logger.info("KnowledgebaseIndexer initialized successfully")
    
    def set_debug(self, debug: bool):
        """Enable or disable debug output."""
        self.debug = debug
        self.search_engine.set_debug(debug)
        self.keyword_processor.set_debug(debug)
    
    def discover_files(self) -> List[str]:
        """Discover files in directories matching glob patterns, filtered by file_types extensions."""
        with LoggedOperation('main', 'file_discovery') as op:
            include_dir_patterns = self.config['directories']['include']
            exclude_dir_patterns = self.config['directories'].get('exclude', [])
            
            # Get supported extensions from file_types
            supported_extensions = set()
            for file_type_config in self.config['file_types'].values():
                supported_extensions.update(file_type_config.get('extensions', []))
            
            AppLogger.log_algorithm_step('main', 'starting_file_discovery', {
                'include_dir_patterns': len(include_dir_patterns),
                'exclude_dir_patterns': len(exclude_dir_patterns),
                'supported_extensions': len(supported_extensions)
            })
            
            self.logger.debug(f"Include directory patterns: {include_dir_patterns}")
            self.logger.debug(f"Exclude directory patterns: {exclude_dir_patterns}")
            self.logger.debug(f"Supported extensions: {sorted(supported_extensions)}")
            
            # Find all directories matching include patterns
            include_directories = set()
            for pattern in include_dir_patterns:
                matches = glob.glob(pattern, recursive=True)
                for match in matches:
                    path = Path(match)
                    if path.is_dir():
                        include_directories.add(path.resolve())
                    elif path.is_file() and path.suffix in supported_extensions:
                        # If pattern matches a file directly, include it
                        include_directories.add(path.parent.resolve())
                
                self.logger.debug(f"Directory pattern '{pattern}' matched {len([m for m in matches if Path(m).is_dir()])} directories")
            
            # Find directories matching exclude patterns  
            exclude_directories = set()
            for pattern in exclude_dir_patterns:
                matches = glob.glob(pattern, recursive=True)
                for match in matches:
                    path = Path(match)
                    if path.is_dir():
                        exclude_directories.add(path.resolve())
                
                if matches:
                    self.logger.debug(f"Exclude pattern '{pattern}' matched {len([m for m in matches if Path(m).is_dir()])} directories")
            
            # Remove excluded directories from include set
            search_directories = include_directories - exclude_directories
            
            # Find all files with supported extensions in the search directories
            all_files = set()
            for directory in search_directories:
                file_count = 0
                try:
                    for file_path in directory.rglob('*'):
                        if file_path.is_file() and file_path.suffix in supported_extensions:
                            # Check if file is in an excluded directory path
                            file_excluded = False
                            for exclude_dir in exclude_directories:
                                try:
                                    if file_path.is_relative_to(exclude_dir):
                                        file_excluded = True
                                        break
                                except ValueError:
                                    # Fallback for older Python versions
                                    if str(exclude_dir) in str(file_path):
                                        file_excluded = True
                                        break
                            
                            if not file_excluded:
                                all_files.add(file_path.resolve())
                                file_count += 1
                    
                    self.logger.debug(f"Directory '{directory}' contained {file_count} matching files")
                    
                except PermissionError:
                    self.logger.warning(f"Permission denied accessing directory: {directory}")
                    continue
            
            # Convert to strings and sort
            result_files = sorted([str(f) for f in all_files])
            
            AppLogger.log_algorithm_step('main', 'file_discovery_complete', {
                'include_dirs_found': len(include_directories),
                'exclude_dirs_found': len(exclude_directories),
                'search_dirs_final': len(search_directories),
                'files_found': len(result_files)
            })
            
            self.logger.info(f"File discovery complete: {len(result_files)} files to process from {len(search_directories)} directories")
            
            return result_files
    
    def create_file_handlers(self, files: List[str]) -> Dict[str, Any]:
        """Create handlers for discovered files."""
        handlers = {}
        file_types_config = self.config['file_types']
        
        for file_path in files:
            handler = handler_registry.get_handler_for_file(file_path, file_types_config)
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
    
    def generate_mind_map(self, file_system_index: Dict[str, List[HierarchicalNode]],
                         keyword_entries: List[Any],
                         tag_results: Dict[str, List[tuple]]) -> str:
        """Generate the final mind map file."""
        output_path = self.config['output']['file']
        
        # Pass hierarchical keyword entries to preserve exact file structure  
        generator = FreeplaneMapGenerator(output_path)
        result_path = generator.create_mind_map(
            file_system_index=file_system_index,
            keyword_entries=keyword_entries,
            tag_results=tag_results,
            config=self.config
        )
        
        return result_path
    
    def run(self) -> str:
        """Run the complete index generation process."""
        try:
            if self.debug:
                print("=== Index Generation Process ===")
            
            # 1. Discover files
            files = self.discover_files()
            if not files:
                raise ValueError("No files found matching the configured patterns")
            
            # 2. Create handlers
            handlers = self.create_file_handlers(files)
            if not handlers:
                raise ValueError("No valid handlers found for discovered files")
            
            # Only process files that have handlers
            valid_files = list(handlers.keys())
            
            # 3. Build file system index
            if self.debug:
                print("\n=== Building File System Index ===")
            file_system_index = self.build_file_system_index(valid_files, handlers)
            
            # 4. Process keyword searches
            if self.debug:
                print("\n=== Processing Keyword Searches ===")
            keyword_entries = self.process_keyword_searches(valid_files, handlers)
            
            # 5. Extract tags
            if self.debug:
                print("\n=== Extracting Tags ===")
            tag_results = self.extract_tags(valid_files, handlers)
            
            # 6. Generate mind map
            if self.debug:
                print("\n=== Generating Mind Map ===")
            output_path = self.generate_mind_map(file_system_index, keyword_entries, tag_results)
            
            return output_path
        
        except Exception as e:
            if self.debug:
                print(f"Error during index generation: {e}")
                traceback.print_exc()
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate navigational mind map indexes for structured file collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate index with default configuration
  python kbi.py
  
  # Use specific configuration file
  python kbi.py --config /path/to/config.yml
  
  # Enable debug output
  python kbi.py --debug
  
  # Specify output file
  python kbi.py --output my_index.mm
  
  # Enable file logging
  python kbi.py --debug --log-file /path/to/debug.log
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file'
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

file_types:
  freeplane:
    extensions: [".mm"]
    handler: "FreeplaneHandler"
  markdown:
    extensions: [".md", ".markdown"]
    handler: "MarkdownHandler"
"""
        
        with open('kbi.yml', 'w') as f:
            f.write(sample_config)
        print("Sample configuration file created: kbi.yml")
        return 0
    
    if args.sample_keywords:
        from keywords import create_sample_keyword_file
        create_sample_keyword_file('keywords.txt')
        return 0
    
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
        
        main_logger.info(f"Configuration loaded from: {args.config or 'defaults'}")
        
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
        print(f"Mind map index generated: {output_path}")
        
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