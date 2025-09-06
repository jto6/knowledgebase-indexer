#!/usr/bin/env python3
"""
Unit tests for hierarchical context-sensitive search functionality.

Tests the search engine and result aggregation components.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from search import (
    HierarchicalSearchEngine, SearchResult, SearchResultAggregator,
    search_files
)
from core_handlers import HierarchicalNode, create_word_boundary_pattern


@pytest.mark.quick
class TestSearchResult:
    """Test cases for SearchResult class."""
    
    def test_search_result_creation(self):
        """Test SearchResult creation."""
        node = HierarchicalNode(id="test", content="test content")
        result = SearchResult(
            file_path="/test/file.md",
            node=node,
            matched_content="test content",
            search_path=["keyword1", "keyword2"]
        )
        
        assert result.file_path == "/test/file.md"
        assert result.node == node
        assert result.matched_content == "test content"
        assert result.search_path == ["keyword1", "keyword2"]
    
    def test_search_result_str(self):
        """Test SearchResult string representation."""
        node = HierarchicalNode(id="test", content="test content", text="Test Node")
        result = SearchResult(
            file_path="/test/file.md",
            node=node,
            matched_content="test content",
            search_path=["keyword1", "keyword2"]
        )
        
        str_repr = str(result)
        assert "/test/file.md" in str_repr
        assert "Test Node" in str_repr
        assert "keyword1 -> keyword2" in str_repr


@pytest.mark.quick
class TestHierarchicalSearchEngine:
    """Test cases for HierarchicalSearchEngine class."""
    
    def test_engine_initialization(self):
        """Test search engine initialization."""
        engine = HierarchicalSearchEngine()
        
        assert engine.debug is False
    
    def test_set_debug(self):
        """Test debug mode setting."""
        engine = HierarchicalSearchEngine()
        engine.set_debug(True)
        
        assert engine.debug is True
    
    def test_search_single_keyword(self):
        """Test single keyword search."""
        engine = HierarchicalSearchEngine()
        
        # Create mock handler and nodes
        mock_handler = Mock()
        root_node = HierarchicalNode(id="root", content="test content", text="Root")
        child_node = HierarchicalNode(id="child", content="other content", text="Child")
        root_node.add_child(child_node)
        
        mock_handler.get_root_nodes.return_value = [root_node]
        mock_handler.search_in_node_subtree.return_value = [root_node]
        mock_handler.get_node_content.return_value = "test content"
        
        files = ["/test/file.md"]
        handlers = {"/test/file.md": mock_handler}
        
        results = engine.search_single_keyword(files, "test", handlers)
        
        assert len(results) == 1
        assert "/test/file.md" in results
        assert len(results["/test/file.md"]) == 1
        assert results["/test/file.md"][0].search_path == ["test"]
    
    def test_search_sequence_two_keywords(self):
        """Test two-keyword search sequence."""
        engine = HierarchicalSearchEngine()
        
        # Create mock handler
        mock_handler = Mock()
        
        # First call: search for "function" in entire file
        root_node = HierarchicalNode(id="root", content="function definition", text="Root")
        child_node = HierarchicalNode(id="child", content="function definition async", text="Child")
        root_node.add_child(child_node)
        
        # Second call: search for "async" within matched nodes
        def side_effect_search(node, pattern, include_descendants):
            if pattern.pattern.find("function") != -1:
                # First search for "function"
                return [child_node]  # Child contains "function"
            elif pattern.pattern.find("async") != -1:
                # Second search for "async" within child_node
                return [child_node]  # Child also contains "async"
            return []
        
        mock_handler.get_root_nodes.return_value = [root_node]
        mock_handler.search_in_node_subtree.side_effect = side_effect_search
        mock_handler.get_node_content.return_value = "function definition async"
        
        files = ["/test/file.md"]
        handlers = {"/test/file.md": mock_handler}
        keywords = ["function", "async"]
        
        results = engine.search_sequence(files, keywords, handlers)
        
        assert len(results) == 1
        assert "/test/file.md" in results
        assert len(results["/test/file.md"]) == 1
        assert results["/test/file.md"][0].search_path == ["function", "async"]
    
    def test_search_sequence_no_matches(self):
        """Test search sequence with no matches."""
        engine = HierarchicalSearchEngine()
        
        mock_handler = Mock()
        mock_handler.get_root_nodes.return_value = []
        mock_handler.search_in_node_subtree.return_value = []
        
        files = ["/test/file.md"]
        handlers = {"/test/file.md": mock_handler}
        
        results = engine.search_sequence(files, ["nonexistent"], handlers)
        
        assert len(results) == 0
    
    def test_search_sequence_empty_keywords(self):
        """Test search with empty keyword list."""
        engine = HierarchicalSearchEngine()
        
        results = engine.search_sequence([], [], {})
        
        assert len(results) == 0
    
    def test_search_multiple_sequences(self):
        """Test searching multiple keyword sequences."""
        engine = HierarchicalSearchEngine()
        
        mock_handler = Mock()
        root_node = HierarchicalNode(id="root", content="function async definition", text="Root")
        
        def side_effect_search(node, pattern, include_descendants):
            content = "function async definition"
            if pattern.search(content):
                return [root_node]
            return []
        
        mock_handler.get_root_nodes.return_value = [root_node]
        mock_handler.search_in_node_subtree.side_effect = side_effect_search
        mock_handler.get_node_content.return_value = "function async definition"
        
        files = ["/test/file.md"]
        handlers = {"/test/file.md": mock_handler}
        sequences = [["function"], ["async"], ["definition"]]
        
        results = engine.search_multiple_sequences(files, sequences, handlers)
        
        assert len(results) == 3
        assert "function" in results
        assert "async" in results
        assert "definition" in results
    
    def test_search_with_handler_error(self):
        """Test search handling errors gracefully."""
        engine = HierarchicalSearchEngine()
        engine.set_debug(True)  # Enable debug for error logging
        
        mock_handler = Mock()
        mock_handler.get_root_nodes.side_effect = Exception("Test error")
        
        files = ["/test/file.md"]
        handlers = {"/test/file.md": mock_handler}
        
        # Should not raise exception, should return empty results
        results = engine.search_sequence(files, ["test"], handlers)
        
        assert len(results) == 0


@pytest.mark.quick
class TestSearchResultAggregator:
    """Test cases for SearchResultAggregator class."""
    
    def create_sample_results(self):
        """Create sample search results for testing."""
        node1 = HierarchicalNode(id="1", content="content1", text="Node 1")
        node2 = HierarchicalNode(id="2", content="content2", text="Node 2")
        node3 = HierarchicalNode(id="3", content="content3", text="Node 3")
        
        results = {
            "/test/file1.md": [
                SearchResult("/test/file1.md", node1, "content1", ["keyword1"]),
                SearchResult("/test/file1.md", node2, "content2", ["keyword2"])
            ],
            "/test/file2.md": [
                SearchResult("/test/file2.md", node3, "content3", ["keyword1"])
            ]
        }
        return results
    
    def test_group_by_file(self):
        """Test grouping results by file."""
        aggregator = SearchResultAggregator()
        results = self.create_sample_results()
        
        grouped = aggregator.group_by_file(results)
        
        # Should be the same as input (already grouped by file)
        assert grouped == results
    
    def test_flatten_results(self):
        """Test flattening nested results."""
        aggregator = SearchResultAggregator()
        results = self.create_sample_results()
        
        flattened = aggregator.flatten_results(results)
        
        assert len(flattened) == 3
        assert all(isinstance(r, SearchResult) for r in flattened)
        
        # Check all files are represented
        file_paths = {r.file_path for r in flattened}
        assert "/test/file1.md" in file_paths
        assert "/test/file2.md" in file_paths
    
    def test_sort_results_by_file_path(self):
        """Test sorting results by file path."""
        aggregator = SearchResultAggregator()
        results = self.create_sample_results()
        flattened = aggregator.flatten_results(results)
        
        sorted_results = aggregator.sort_results(flattened, "file_path")
        
        # Should be sorted by file path, then by node text
        assert sorted_results[0].file_path == "/test/file1.md"
        assert sorted_results[1].file_path == "/test/file1.md"
        assert sorted_results[2].file_path == "/test/file2.md"
    
    def test_sort_results_by_node_text(self):
        """Test sorting results by node text."""
        aggregator = SearchResultAggregator()
        results = self.create_sample_results()
        flattened = aggregator.flatten_results(results)
        
        sorted_results = aggregator.sort_results(flattened, "node_text")
        
        # Should be sorted by node text
        node_texts = [r.node.text for r in sorted_results]
        assert node_texts == sorted(node_texts)
    
    def test_sort_results_by_search_path(self):
        """Test sorting results by search path length."""
        aggregator = SearchResultAggregator()
        
        # Create results with different search path lengths
        node1 = HierarchicalNode(id="1", content="content1", text="Node 1")
        node2 = HierarchicalNode(id="2", content="content2", text="Node 2")
        
        results_list = [
            SearchResult("/test/file.md", node1, "content1", ["a", "b", "c"]),  # Length 3
            SearchResult("/test/file.md", node2, "content2", ["a"])  # Length 1
        ]
        
        sorted_results = aggregator.sort_results(results_list, "search_path")
        
        # Should be sorted by search path length (shorter first)
        assert len(sorted_results[0].search_path) == 1
        assert len(sorted_results[1].search_path) == 3
    
    def test_filter_by_file_type(self):
        """Test filtering results by file extensions."""
        aggregator = SearchResultAggregator()
        
        node1 = HierarchicalNode(id="1", content="content1")
        node2 = HierarchicalNode(id="2", content="content2")
        node3 = HierarchicalNode(id="3", content="content3")
        
        results_list = [
            SearchResult("/test/file1.md", node1, "content1", ["keyword"]),
            SearchResult("/test/file2.mm", node2, "content2", ["keyword"]),
            SearchResult("/test/file3.txt", node3, "content3", ["keyword"])
        ]
        
        filtered = aggregator.filter_by_file_type(results_list, [".md", ".mm"])
        
        assert len(filtered) == 2
        assert all(r.file_path.endswith((".md", ".mm")) for r in filtered)
    
    def test_deduplicate_results(self):
        """Test deduplicating search results."""
        aggregator = SearchResultAggregator()
        
        node1 = HierarchicalNode(id="1", content="content1")
        node2 = HierarchicalNode(id="2", content="content2")
        
        # Create duplicates (same file and node ID)
        results_list = [
            SearchResult("/test/file.md", node1, "content1", ["keyword1"]),
            SearchResult("/test/file.md", node1, "content1", ["keyword2"]),  # Duplicate node
            SearchResult("/test/file.md", node2, "content2", ["keyword1"])
        ]
        
        deduplicated = aggregator.deduplicate_results(results_list)
        
        assert len(deduplicated) == 2  # Should remove one duplicate
        
        # Check that we have one result for each unique (file, node_id) pair
        seen_keys = set()
        for result in deduplicated:
            key = (result.file_path, result.node.id)
            assert key not in seen_keys
            seen_keys.add(key)


@pytest.mark.quick
class TestConvenienceFunctions:
    """Test cases for convenience search functions."""
    
    def test_search_files_function(self):
        """Test the search_files convenience function."""
        # Create mock handler
        mock_handler = Mock()
        root_node = HierarchicalNode(id="root", content="python function definition", text="Root")
        
        def side_effect_search(node, pattern, include_descendants):
            content = "python function definition"
            if pattern.search(content):
                return [root_node]
            return []
        
        mock_handler.get_root_nodes.return_value = [root_node]
        mock_handler.search_in_node_subtree.side_effect = side_effect_search
        mock_handler.get_node_content.return_value = "python function definition"
        
        files = ["/test/file.py"]
        handlers = {"/test/file.py": mock_handler}
        
        results = search_files(files, "python:function", handlers, debug=False)
        
        assert len(results) == 1
        assert "/test/file.py" in results
        assert len(results["/test/file.py"]) == 1
        assert results["/test/file.py"][0].search_path == ["python", "function"]
    
    def test_search_files_debug_mode(self):
        """Test search_files with debug mode enabled."""
        mock_handler = Mock()
        mock_handler.get_root_nodes.return_value = []
        mock_handler.search_in_node_subtree.return_value = []
        
        files = ["/test/file.py"]
        handlers = {"/test/file.py": mock_handler}
        
        # Should not raise exception even in debug mode
        results = search_files(files, "test", handlers, debug=True)
        
        assert len(results) == 0


@pytest.mark.quick
class TestSearchIntegration:
    """Integration tests for search functionality."""
    
    def test_realistic_search_scenario(self):
        """Test a realistic multi-level search scenario."""
        engine = HierarchicalSearchEngine()
        
        # Create realistic node hierarchy
        root = HierarchicalNode(id="root", content="Python programming guide", text="Python Guide")
        
        functions_section = HierarchicalNode(
            id="functions", 
            content="This section covers function definitions in Python",
            text="Functions Section"
        )
        
        async_subsection = HierarchicalNode(
            id="async",
            content="Async function definitions use async def syntax",
            text="Async Functions"
        )
        
        example_node = HierarchicalNode(
            id="example",
            content="async def example(): return await something()",
            text="Example Code"
        )
        
        # Build hierarchy
        root.add_child(functions_section)
        functions_section.add_child(async_subsection)
        async_subsection.add_child(example_node)
        
        # Create mock handler that simulates realistic search behavior
        mock_handler = Mock()
        mock_handler.get_root_nodes.return_value = [root]
        mock_handler.get_node_content.side_effect = lambda node: node.content
        
        def realistic_search(node, pattern, include_descendants):
            """Simulate realistic hierarchical search."""
            matches = []
            content = node.content
            
            if pattern.search(content):
                matches.append(node)
                if not include_descendants:
                    return matches
            
            if include_descendants:
                for child in node.children:
                    child_matches = realistic_search(child, pattern, include_descendants)
                    matches.extend(child_matches)
                    if not include_descendants and child_matches:
                        break
            
            return matches
        
        mock_handler.search_in_node_subtree.side_effect = realistic_search
        
        files = ["/test/python_guide.md"]
        handlers = {"/test/python_guide.md": mock_handler}
        
        # Search for "function:async" sequence
        results = engine.search_sequence(files, ["function", "async"], handlers)
        
        assert len(results) == 1
        assert "/test/python_guide.md" in results
        
        # Should find the async subsection and example
        file_results = results["/test/python_guide.md"]
        assert len(file_results) >= 1
        
        # Check that search path is preserved
        for result in file_results:
            assert result.search_path == ["function", "async"]