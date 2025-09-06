#!/usr/bin/env python3
"""
Unit tests for file handlers and handler registry.

Tests the base FileHandler class, HierarchicalNode, and HandlerRegistry.
"""

import pytest
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_handlers import (
    FileHandler, HierarchicalNode, HandlerRegistry, 
    generate_unique_id, get_current_timestamp, create_word_boundary_pattern
)


@pytest.mark.quick
class TestHierarchicalNode:
    """Test cases for HierarchicalNode class."""
    
    def test_node_creation(self):
        """Test basic node creation."""
        node = HierarchicalNode(
            id="test_id",
            content="Test content",
            text="Test text",
            file_path="/test/file.md"
        )
        
        assert node.id == "test_id"
        assert node.content == "Test content"
        assert node.text == "Test text"
        assert node.file_path == "/test/file.md"
        assert node.children == []
        assert node.parent is None
        assert node.metadata == {}
    
    def test_node_with_defaults(self):
        """Test node creation with default values."""
        node = HierarchicalNode(id="test", content="content")
        
        assert node.text == "content"  # Should default to content
        assert node.children is not None
        assert node.metadata is not None
    
    def test_add_child(self):
        """Test adding child nodes."""
        parent = HierarchicalNode(id="parent", content="Parent")
        child = HierarchicalNode(id="child", content="Child")
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert child.parent == parent
    
    def test_get_descendants(self):
        """Test getting all descendant nodes."""
        root = HierarchicalNode(id="root", content="Root")
        child1 = HierarchicalNode(id="child1", content="Child 1")
        child2 = HierarchicalNode(id="child2", content="Child 2")
        grandchild = HierarchicalNode(id="grandchild", content="Grandchild")
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)
        
        descendants = root.get_descendants()
        
        assert len(descendants) == 3
        assert child1 in descendants
        assert child2 in descendants
        assert grandchild in descendants
    
    def test_find_children_by_type(self):
        """Test finding children by node type."""
        parent = HierarchicalNode(id="parent", content="Parent")
        
        child1 = HierarchicalNode(id="child1", content="Child 1", node_type="heading")
        child2 = HierarchicalNode(id="child2", content="Child 2", node_type="list_item")
        child3 = HierarchicalNode(id="child3", content="Child 3", node_type="heading")
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)
        
        headings = parent.find_children_by_type("heading")
        lists = parent.find_children_by_type("list_item")
        
        assert len(headings) == 2
        assert child1 in headings
        assert child3 in headings
        assert len(lists) == 1
        assert child2 in lists
    
    def test_get_path(self):
        """Test getting path from root to node."""
        root = HierarchicalNode(id="root", content="Root", text="Root")
        child = HierarchicalNode(id="child", content="Child", text="Child")
        grandchild = HierarchicalNode(id="grandchild", content="Grandchild", text="Grandchild")
        
        root.add_child(child)
        child.add_child(grandchild)
        
        path = grandchild.get_path()
        
        assert path == ["Root", "Child", "Grandchild"]


@pytest.mark.quick
class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_generate_unique_id(self):
        """Test unique ID generation."""
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        
        assert id1 != id2
        assert id1.startswith("ID_")
        assert id2.startswith("ID_")
        assert len(id1) > 10  # Should be reasonably long
    
    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        timestamp = get_current_timestamp()
        
        assert len(timestamp) == 15  # YYYYMMDDTHHMMSS format
        assert timestamp[8] == 'T'  # Should have T separator
        assert timestamp.isalnum()  # Should be alphanumeric except for T
    
    def test_create_word_boundary_pattern(self):
        """Test word boundary pattern creation."""
        pattern = create_word_boundary_pattern("test")
        
        assert isinstance(pattern, re.Pattern)
        assert pattern.flags & re.IGNORECASE  # Should be case insensitive
        
        # Test matching
        assert pattern.search("test word")
        assert pattern.search("word test")
        assert pattern.search("Test Word")  # Case insensitive
        assert not pattern.search("testing")  # Should not match partial words
        assert not pattern.search("contest")  # Should not match partial words
    
    def test_create_word_boundary_pattern_special_chars(self):
        """Test pattern creation with special regex characters."""
        pattern = create_word_boundary_pattern("C++")
        
        # Should escape special characters
        assert pattern.search("C++ programming")
        assert not pattern.search("C++++")  # But still use word boundaries


class MockFileHandler(FileHandler):
    """Mock file handler for testing base class."""
    
    def __init__(self, config):
        super().__init__(config)
        self.test_nodes = []
    
    def can_handle(self, file_path: str) -> bool:
        return file_path.endswith('.test')
    
    def get_root_nodes(self, file_path: str):
        return self.test_nodes
    
    def get_child_nodes(self, parent_node):
        return parent_node.children
    
    def get_node_content(self, node):
        return node.content


@pytest.mark.quick
class TestFileHandler:
    """Test cases for base FileHandler class."""
    
    def test_handler_initialization(self, sample_config):
        """Test handler initialization with config."""
        file_type_config = sample_config['file_types']['markdown']
        handler = MockFileHandler(file_type_config)
        
        assert handler.config == file_type_config
        assert handler.hierarchy_config == file_type_config.get('hierarchy_config', {})
        assert handler.search_config == file_type_config.get('search_config', {})
        assert handler.link_config == file_type_config.get('link_config', {})
    
    def test_search_in_node_subtree_single_match(self):
        """Test searching in node subtree with single match."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        # Create test hierarchy
        root = HierarchicalNode(id="root", content="root content")
        child1 = HierarchicalNode(id="child1", content="test content")
        child2 = HierarchicalNode(id="child2", content="other content")
        
        root.add_child(child1)
        root.add_child(child2)
        
        pattern = create_word_boundary_pattern("test")
        results = handler.search_in_node_subtree(root, pattern, include_descendants=True)
        
        assert len(results) == 1
        assert results[0] == child1
    
    def test_search_in_node_subtree_early_termination(self):
        """Test early termination when include_descendants=False."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        # Create test hierarchy where root matches
        root = HierarchicalNode(id="root", content="test content")
        child = HierarchicalNode(id="child", content="test content too")
        root.add_child(child)
        
        pattern = create_word_boundary_pattern("test")
        results = handler.search_in_node_subtree(root, pattern, include_descendants=False)
        
        # Should only return root due to early termination
        assert len(results) == 1
        assert results[0] == root
    
    def test_extract_tags_default(self):
        """Test default tag extraction (should return empty list)."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        tags = handler.extract_tags("test.txt")
        assert tags == []
    
    def test_generate_link_simple(self, temp_dir):
        """Test simple link generation."""
        config = {"link_config": {"format": "{path}", "supports_fragments": False}}
        handler = MockFileHandler(config)
        
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")
        
        # Change to temp directory to test relative path generation
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(str(temp_dir))
            link = handler.generate_link(str(test_file))
            assert link == "test.txt"
        finally:
            os.chdir(original_cwd)
    
    def test_generate_link_with_fragment(self, temp_dir):
        """Test link generation with fragment."""
        config = {
            "link_config": {
                "format": "{path}#{fragment}",
                "supports_fragments": True
            }
        }
        handler = MockFileHandler(config)
        
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(str(temp_dir))
            link = handler.generate_link(str(test_file), "node_123")
            assert link == "test.txt#node_123"
        finally:
            os.chdir(original_cwd)
    
    def test_validate_file_exists(self, temp_dir):
        """Test file validation for existing file."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        test_file = temp_dir / "valid.test"
        test_file.write_text("content")
        
        assert handler.validate_file(str(test_file))
    
    def test_validate_file_wrong_extension(self, temp_dir):
        """Test file validation for wrong extension."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        test_file = temp_dir / "invalid.txt"
        test_file.write_text("content")
        
        assert not handler.validate_file(str(test_file))
    
    def test_validate_file_not_exists(self):
        """Test file validation for non-existent file."""
        config = {"extensions": [".test"]}
        handler = MockFileHandler(config)
        
        assert not handler.validate_file("/nonexistent/file.test")


@pytest.mark.quick
class TestHandlerRegistry:
    """Test cases for HandlerRegistry class."""
    
    def test_registry_initialization(self):
        """Test registry starts empty."""
        registry = HandlerRegistry()
        
        assert len(registry._handlers) == 0
        assert len(registry._instances) == 0
    
    def test_register_handler(self):
        """Test handler registration."""
        registry = HandlerRegistry()
        registry.register_handler("TestHandler", MockFileHandler)
        
        assert "TestHandler" in registry._handlers
        assert registry._handlers["TestHandler"] == MockFileHandler
    
    def test_get_handler_new_instance(self):
        """Test getting handler creates new instance."""
        registry = HandlerRegistry()
        registry.register_handler("TestHandler", MockFileHandler)
        
        config = {"extensions": [".test"]}
        handler = registry.get_handler("TestHandler", config)
        
        assert isinstance(handler, MockFileHandler)
        assert handler.config == config
        assert "TestHandler" in registry._instances
    
    def test_get_handler_cached_instance(self):
        """Test getting handler returns cached instance."""
        registry = HandlerRegistry()
        registry.register_handler("TestHandler", MockFileHandler)
        
        config = {"extensions": [".test"]}
        handler1 = registry.get_handler("TestHandler", config)
        handler2 = registry.get_handler("TestHandler", config)
        
        assert handler1 is handler2  # Should be same instance
    
    def test_get_handler_nonexistent(self):
        """Test getting non-existent handler returns None."""
        registry = HandlerRegistry()
        
        handler = registry.get_handler("NonExistentHandler", {})
        assert handler is None
    
    def test_get_handler_for_file(self, temp_dir):
        """Test finding handler for specific file."""
        registry = HandlerRegistry()
        registry.register_handler("TestHandler", MockFileHandler)
        
        test_file = temp_dir / "test.test"
        test_file.write_text("content")
        
        file_types_config = {
            "test_type": {
                "handler": "TestHandler",
                "extensions": [".test"]
            }
        }
        
        handler = registry.get_handler_for_file(str(test_file), file_types_config)
        
        assert isinstance(handler, MockFileHandler)
    
    def test_get_handler_for_file_no_match(self, temp_dir):
        """Test finding handler when no handler matches."""
        registry = HandlerRegistry()
        registry.register_handler("TestHandler", MockFileHandler)
        
        test_file = temp_dir / "test.txt"  # Different extension
        test_file.write_text("content")
        
        file_types_config = {
            "test_type": {
                "handler": "TestHandler",
                "extensions": [".test"]  # Doesn't match .txt
            }
        }
        
        handler = registry.get_handler_for_file(str(test_file), file_types_config)
        
        assert handler is None