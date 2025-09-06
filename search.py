#!/usr/bin/env python3
"""Hierarchical context-sensitive search implementation."""

import re
from typing import List, Dict, Any, DefaultDict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from core_handlers import FileHandler, HierarchicalNode, create_word_boundary_pattern, create_word_boundary_regex_pattern


@dataclass
class SearchResult:
    """Represents a search result."""
    file_path: str
    node: HierarchicalNode
    matched_content: str
    search_path: List[str]  # The sequence of keywords that led to this match
    
    def __str__(self):
        return f"{self.file_path}: {self.node.text} (Path: {' -> '.join(self.search_path)})"


class HierarchicalSearchEngine:
    """Implements hierarchical context-sensitive search."""
    
    def __init__(self):
        self.debug = False
    
    def set_debug(self, debug: bool):
        """Enable or disable debug output."""
        self.debug = debug
    
    def search_sequence(self, files: List[str], keyword_sequence: List[str], 
                       handlers: Dict[str, FileHandler]) -> Dict[str, List[SearchResult]]:
        """
        Execute hierarchical context-sensitive search sequence.
        
        Args:
            files: List of file paths to search
            keyword_sequence: List of keywords in search sequence (colon-separated from original)
            handlers: Dict mapping file paths to their handlers
        
        Returns:
            Dict mapping file paths to lists of SearchResult objects
        """
        if not keyword_sequence:
            return {}
        
        if self.debug:
            print(f"Searching sequence: {keyword_sequence}")
        
        # Track current matches through the sequence
        current_matches: DefaultDict[str, List[Tuple[HierarchicalNode, List[str]]]] = defaultdict(list)
        
        # First keyword: search entire files
        first_keyword = keyword_sequence[0]
        first_pattern = create_word_boundary_regex_pattern(first_keyword)
        
        if self.debug:
            print(f"First keyword: '{first_keyword}'")
        
        for file_path in files:
            handler = handlers.get(file_path)
            if not handler:
                continue
            
            try:
                root_nodes = handler.get_root_nodes(file_path)
                for root in root_nodes:
                    # Search in entire tree for first keyword
                    is_last = len(keyword_sequence) == 1
                    matches = handler.search_in_node_subtree(root, first_pattern, 
                                                           include_descendants=True)
                    
                    for match in matches:
                        search_path = [first_keyword]
                        current_matches[file_path].append((match, search_path))
                        
                        if self.debug:
                            print(f"  Found in {file_path}: {match.text}")
            
            except Exception as e:
                if self.debug:
                    print(f"Error searching {file_path}: {e}")
                continue
        
        # Process subsequent keywords
        for i, keyword in enumerate(keyword_sequence[1:], 1):
            is_last = (i == len(keyword_sequence) - 1)
            keyword_pattern = create_word_boundary_regex_pattern(keyword)
            new_matches: DefaultDict[str, List[Tuple[HierarchicalNode, List[str]]]] = defaultdict(list)
            
            if self.debug:
                print(f"Processing keyword {i+1}: '{keyword}' (is_last: {is_last})")
            
            for file_path, node_matches in current_matches.items():
                handler = handlers[file_path]
                
                for node, search_path in node_matches:
                    # Search within this node AND its entire subtree
                    try:
                        subtree_matches = handler.search_in_node_subtree(
                            node, keyword_pattern, include_descendants=is_last)
                        
                        for match in subtree_matches:
                            new_search_path = search_path + [keyword]
                            new_matches[file_path].append((match, new_search_path))
                            
                            if self.debug:
                                print(f"  Refined match in {file_path}: {match.text}")
                    
                    except Exception as e:
                        if self.debug:
                            print(f"Error searching subtree in {file_path}: {e}")
                        continue
            
            current_matches = new_matches
            if not current_matches:
                if self.debug:
                    print(f"No matches found for keyword '{keyword}', stopping search")
                break
        
        # Convert to SearchResult objects
        results: Dict[str, List[SearchResult]] = {}
        for file_path, node_matches in current_matches.items():
            file_results = []
            for node, search_path in node_matches:
                handler = handlers[file_path]
                matched_content = handler.get_node_content(node)
                
                result = SearchResult(
                    file_path=file_path,
                    node=node,
                    matched_content=matched_content,
                    search_path=search_path
                )
                file_results.append(result)
            
            if file_results:
                results[file_path] = file_results
        
        return results
    
    def search_single_keyword(self, files: List[str], keyword: str, 
                            handlers: Dict[str, FileHandler]) -> Dict[str, List[SearchResult]]:
        """Search for a single keyword across files."""
        return self.search_sequence(files, [keyword], handlers)
    
    def search_multiple_sequences(self, files: List[str], keyword_sequences: List[List[str]], 
                                handlers: Dict[str, FileHandler]) -> Dict[str, Dict[str, List[SearchResult]]]:
        """
        Search multiple keyword sequences.
        
        Args:
            files: List of file paths to search
            keyword_sequences: List of keyword sequences to search
            handlers: Dict mapping file paths to their handlers
        
        Returns:
            Dict mapping sequence identifiers to search results
        """
        all_results = {}
        
        for i, sequence in enumerate(keyword_sequences):
            sequence_id = ':'.join(sequence)
            if self.debug:
                print(f"\n=== Searching sequence {i+1}: {sequence_id} ===")
            
            results = self.search_sequence(files, sequence, handlers)
            if results:
                all_results[sequence_id] = results
        
        return all_results


class SearchResultAggregator:
    """Aggregates and organizes search results."""
    
    def group_by_file(self, results: Dict[str, List[SearchResult]]) -> Dict[str, List[SearchResult]]:
        """Group results by file (already grouped, but ensures consistency)."""
        return results
    
    def group_by_keyword_sequence(self, results: Dict[str, Dict[str, List[SearchResult]]]) -> Dict[str, Dict[str, List[SearchResult]]]:
        """Group results by keyword sequence."""
        return results
    
    def flatten_results(self, results: Dict[str, List[SearchResult]]) -> List[SearchResult]:
        """Flatten nested results into a single list."""
        flattened = []
        for file_results in results.values():
            flattened.extend(file_results)
        return flattened
    
    def sort_results(self, results: List[SearchResult], 
                    sort_by: str = 'file_path') -> List[SearchResult]:
        """Sort results by specified criteria."""
        if sort_by == 'file_path':
            return sorted(results, key=lambda r: (r.file_path, r.node.text))
        elif sort_by == 'node_text':
            return sorted(results, key=lambda r: (r.node.text, r.file_path))
        elif sort_by == 'search_path':
            return sorted(results, key=lambda r: (len(r.search_path), r.file_path, r.node.text))
        else:
            return results
    
    def filter_by_file_type(self, results: List[SearchResult], 
                          file_extensions: List[str]) -> List[SearchResult]:
        """Filter results by file extensions."""
        return [r for r in results if any(r.file_path.endswith(ext) for ext in file_extensions)]
    
    def deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results (same file and node)."""
        seen = set()
        deduplicated = []
        
        for result in results:
            key = (result.file_path, result.node.id)
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
        
        return deduplicated


# Convenience functions for common search patterns

def search_files(files: List[str], keywords: str, handlers: Dict[str, FileHandler], 
                debug: bool = False) -> Dict[str, List[SearchResult]]:
    """
    Convenience function to search files with a keyword string.
    
    Args:
        files: List of file paths to search
        keywords: Colon-separated keyword sequence (e.g., "python:function:async")
        handlers: Dict mapping file paths to their handlers
        debug: Enable debug output
    
    Returns:
        Dict mapping file paths to search results
    """
    engine = HierarchicalSearchEngine()
    engine.set_debug(debug)
    
    keyword_sequence = [kw.strip() for kw in keywords.split(':')]
    return engine.search_sequence(files, keyword_sequence, handlers)