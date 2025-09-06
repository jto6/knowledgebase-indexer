#!/usr/bin/env python3
"""
Quick commit tests for Knowledgebase Indexer.

These tests run quickly and verify core functionality works.
Used for rapid feedback during development and CI/CD.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigLoader
from core_handlers import generate_unique_id, get_current_timestamp, create_word_boundary_pattern
from core_handlers import HierarchicalNode, HandlerRegistry
from keywords import KeywordEntry, KeywordFileParser
from search import HierarchicalSearchEngine, SearchResult
from mindmap_generator import FreeplaneMapGenerator


@pytest.mark.quick
class TestQuickSmoke:
    """Smoke tests that verify basic functionality quickly."""
    
    def test_imports_work(self):
        """Test that all main modules import without errors."""
        # If we get here, imports worked
        assert True
    
    def test_config_loader_basic(self):
        """Test basic config loading functionality."""
        loader = ConfigLoader()
        config = loader._get_default_config()
        
        assert 'directories' in config
        assert 'output' in config
        assert 'file_types' in config
        assert isinstance(config['directories']['include'], list)
    
    def test_unique_id_generation(self):
        """Test unique ID generation works."""
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        
        assert id1 != id2
        assert id1.startswith('ID_')
        assert len(id1) > 5
    
    def test_timestamp_generation(self):
        """Test timestamp generation works."""
        timestamp = get_current_timestamp()
        
        assert len(timestamp) == 15
        assert timestamp[8] == 'T'
        assert timestamp.replace('T', '').isdigit()
    
    def test_word_boundary_pattern(self):
        """Test regex pattern creation."""
        pattern = create_word_boundary_pattern("test")
        
        assert pattern.search("test word") is not None
        assert pattern.search("testing") is None  # Should not match partial
        assert pattern.search("contest") is None  # Should not match partial


@pytest.mark.quick
class TestQuickCore:
    """Quick tests for core components."""
    
    def test_hierarchical_node_basic(self):
        """Test basic node operations."""
        node = HierarchicalNode(id="test", content="content")
        child = HierarchicalNode(id="child", content="child content")
        
        node.add_child(child)
        
        assert len(node.children) == 1
        assert child.parent == node
        assert node.get_descendants() == [child]
    
    def test_keyword_entry_basic(self):
        """Test basic keyword entry operations."""
        entry = KeywordEntry("test:keyword", 1, True)
        
        sequences = entry.get_search_sequences()
        assert len(sequences) == 1
        assert sequences[0] == ["test", "keyword"]
        
        display = entry.get_display_name()
        assert display == "test → keyword"
    
    def test_search_result_creation(self):
        """Test search result creation."""
        node = HierarchicalNode(id="test", content="content")
        result = SearchResult("/test.md", node, "matched", ["keyword"])
        
        assert result.file_path == "/test.md"
        assert result.node == node
        assert result.matched_content == "matched"
        assert result.search_path == ["keyword"]
    
    def test_handler_registry_basic(self):
        """Test handler registry basic operations."""
        registry = HandlerRegistry()
        
        class MockHandler:
            def __init__(self, config):
                self.config = config
        
        registry.register_handler("TestHandler", MockHandler)
        handler = registry.get_handler("TestHandler", {"test": "config"})
        
        assert handler is not None
        assert handler.config == {"test": "config"}
    
    def test_search_engine_creation(self):
        """Test search engine can be created."""
        engine = HierarchicalSearchEngine()
        
        assert engine.debug is False
        
        engine.set_debug(True)
        assert engine.debug is True


@pytest.mark.quick  
class TestQuickParser:
    """Quick tests for parsing functionality."""
    
    def test_keyword_parser_simple(self):
        """Test simple keyword parsing."""
        parser = KeywordFileParser()
        lines = [
            "Category\n",
            "\tkeyword1\n",
            "\tkeyword2:sequence\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        assert entries[0].text == "Category"
        assert len(entries[0].children) == 2
        
        sequences = entries[0].get_search_sequences()
        assert ["keyword1"] in sequences
        assert ["keyword2", "sequence"] in sequences
    
    def test_keyword_parser_comments(self):
        """Test keyword parser handles comments."""
        parser = KeywordFileParser()
        lines = [
            "# Comment\n",
            "Category\n",
            "\t# Another comment\n", 
            "\tkeyword\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        assert entries[0].text == "Category"
        assert len(entries[0].children) == 1
        assert entries[0].children[0].text == "keyword"
    
    def test_indentation_calculation(self):
        """Test indentation level calculation."""
        parser = KeywordFileParser()
        
        assert parser._calculate_indentation_level("no indent") == 0
        assert parser._calculate_indentation_level("\tone tab") == 1
        assert parser._calculate_indentation_level("\t\ttwo tabs") == 2
        assert parser._calculate_indentation_level("    four spaces") == 1


@pytest.mark.quick
class TestQuickXML:
    """Quick tests for XML generation."""
    
    def test_xml_generation_basic(self):
        """Test basic XML mind map generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.mm"
            generator = FreeplaneMapGenerator(str(output_path))
            
            # Create minimal test data
            file_index = {"test.md": []}
            keyword_results = {}
            tag_results = {}
            config = {}
            
            result_path = generator.create_mind_map(
                file_index, keyword_results, tag_results, config
            )
            
            assert Path(result_path).exists()
            
            # Parse and validate basic structure
            tree = ET.parse(result_path)
            root = tree.getroot()
            
            assert root.tag == "map"
            assert root.get("version") == "freeplane 1.12.1"
            
            # Should have main navigation node
            main_node = root.find(".//node[@TEXT='Navigation Index']")
            assert main_node is not None
    
    def test_xml_node_creation(self):
        """Test XML node creation with proper attributes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.mm"
            generator = FreeplaneMapGenerator(str(output_path))
            
            # Generate a test XML structure
            file_index = {"test.md": []}
            keyword_results = {}
            tag_results = {}
            
            generator.create_mind_map(file_index, keyword_results, tag_results, {})
            
            # Parse and check node attributes
            tree = ET.parse(output_path)
            nodes = tree.findall(".//node")
            
            for node in nodes:
                # Each node should have required attributes
                assert node.get("ID") is not None
                assert node.get("CREATED") is not None
                assert node.get("MODIFIED") is not None
                assert node.get("TEXT") is not None
                
                # IDs should be unique and properly formatted
                node_id = node.get("ID")
                assert node_id.startswith("ID_")
                assert len(node_id) > 5


@pytest.mark.quick
class TestQuickIntegration:
    """Quick integration tests that verify components work together."""
    
    def test_config_to_xml_pipeline(self):
        """Test basic config to XML generation pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create simple test file
            test_file = temp_path / "test.md"
            test_file.write_text("# Test\nContent here.")
            
            # Create minimal working config
            config = {
                "directories": {
                    "include": [str(test_file)],  # Include specific file
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": str(temp_path / "output.mm")
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    }
                }
            }
            
            # Test that we can create components with this config
            loader = ConfigLoader()
            loader.validate_config(config)  # Should not raise
            
            generator = FreeplaneMapGenerator(config["output"]["file"])
            
            # Test basic XML generation
            file_index = {str(test_file): []}
            output_path = generator.create_mind_map(file_index, {}, {}, config)
            
            assert Path(output_path).exists()
    
    def test_search_with_mock_handler(self):
        """Test search functionality with mock handler."""
        engine = HierarchicalSearchEngine()
        
        # Create mock node structure
        root_node = HierarchicalNode(id="root", content="python function definition")
        
        # Create mock handler
        class MockHandler:
            def get_root_nodes(self, file_path):
                return [root_node]
            
            def search_in_node_subtree(self, node, pattern, include_descendants):
                if pattern.search(node.content):
                    return [node]
                return []
            
            def get_node_content(self, node):
                return node.content
        
        handler = MockHandler()
        files = ["test.py"]
        handlers = {"test.py": handler}
        
        # Test single keyword search
        results = engine.search_single_keyword(files, "python", handlers)
        
        assert len(results) == 1
        assert "test.py" in results
        assert len(results["test.py"]) == 1
        assert results["test.py"][0].search_path == ["python"]
    
    def test_end_to_end_minimal(self):
        """Minimal end-to-end test without file I/O."""
        # Test that all major components can be instantiated
        loader = ConfigLoader()
        config = loader._get_default_config()
        
        engine = HierarchicalSearchEngine()
        parser = KeywordFileParser()
        registry = HandlerRegistry()
        
        # Test basic operations
        node = HierarchicalNode(id="test", content="content")
        entry = KeywordEntry("test", 1, True)
        
        assert loader is not None
        assert engine is not None
        assert parser is not None
        assert registry is not None
        assert node is not None
        assert entry is not None


if __name__ == "__main__":
    # Run quick tests only
    pytest.main([__file__, "-m", "quick", "-v"])