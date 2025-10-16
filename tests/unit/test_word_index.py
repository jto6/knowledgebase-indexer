#!/usr/bin/env python3
"""
Unit tests for word index generation in mindmap output.

Tests the integration of word filtering with mindmap generation
according to requirements R-WORD-001 to R-WORD-015.
"""

import pytest
import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mindmap_generator import FreeplaneMapGenerator
from word_filter import SignificantWordFilter


class TestWordIndexGeneration:
    """Test cases for word index generation in mindmap output."""
    
    @pytest.fixture
    def temp_output_file(self):
        """Create temporary output file for testing."""
        fd, path = tempfile.mkstemp(suffix='.mm')
        yield path
        os.close(fd)
        os.unlink(path)
    
    @pytest.fixture
    def generator(self, temp_output_file):
        """Create FreeplaneMapGenerator instance for testing."""
        return FreeplaneMapGenerator(temp_output_file)
    
    def test_word_index_creation(self, generator, temp_output_file):
        """Test R-WORD-001: Word Index as fourth main branch of mind map output."""
        # Sample data
        file_system_index = {}
        keyword_entries = []
        tag_results = {}
        word_results = {
            'python': ['/test/file1.py', '/test/file2.py'],
            'programming': ['/test/file1.py'],
            'algorithm': ['/test/file2.py', '/test/file3.py'],
        }
        
        config = {}
        
        # Generate mindmap
        result_path = generator.create_mind_map(
            file_system_index=file_system_index,
            keyword_entries=keyword_entries,
            tag_results=tag_results,
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the main navigation node
        nav_node = root.find('.//node[@TEXT="Navigation Index"]')
        assert nav_node is not None, "Navigation Index node not found"
        
        # Find the Word Index node
        word_index_node = nav_node.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None, "Word Index node not found"
        
        # Verify word nodes exist
        word_nodes = word_index_node.findall('.//node')
        word_texts = [node.get('TEXT') for node in word_nodes]
        
        assert 'python' in word_texts
        assert 'programming' in word_texts  
        assert 'algorithm' in word_texts
    
    def test_word_index_only_when_words_exist(self, generator, temp_output_file):
        """Test that Word Index is only created when words are found."""
        # Sample data with no word results
        file_system_index = {'/test': []}
        keyword_entries = []
        tag_results = {}
        word_results = {}  # Empty word results
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index=file_system_index,
            keyword_entries=keyword_entries,
            tag_results=tag_results,
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the main navigation node
        nav_node = root.find('.//node[@TEXT="Navigation Index"]')
        assert nav_node is not None
        
        # Word Index should not exist when no words found
        word_index_node = nav_node.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is None, "Word Index should not exist when no words found"
    
    def test_hierarchical_word_grouping_max_24_children(self, generator, temp_output_file):
        """Test R-WORD-006: Maximum 24 children per node at any level."""
        # Create word results with many words to force grouping
        word_results = {}
        
        # Create 30 words starting with 'a' to force character grouping
        for i in range(30):
            word = f"a{chr(ord('a') + (i % 26))}{i:02d}word"
            word_results[word] = [f'/test/file{i}.py']
        
        # Add some words with other starting letters
        word_results['beta'] = ['/test/beta.py']
        word_results['gamma'] = ['/test/gamma.py']
        word_results['delta'] = ['/test/delta.py']
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the Word Index node
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None
        
        # Recursively check that no node has more than 24 children
        def check_max_children(node):
            children = node.findall('./node')  # Direct children only
            assert len(children) <= 24, f"Node '{node.get('TEXT')}' has {len(children)} children, exceeds limit of 24"
            
            for child in children:
                check_max_children(child)
        
        check_max_children(word_index_node)
    
    def test_word_file_links_format(self, generator, temp_output_file):
        """Test R-WORD-012: File links under word nodes use same format as File System Index."""
        word_results = {
            'python': ['/test/script.py', '/test/module.py'],
            'testing': ['/test/test_file.py']
        }
        
        config = {}
        
        # Generate mindmap  
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find word nodes and their file children
        word_nodes = root.findall('.//node[@TEXT="python"]')
        assert len(word_nodes) >= 1
        
        python_node = word_nodes[0]
        file_nodes = python_node.findall('./node')
        
        # Should have file nodes with proper links
        assert len(file_nodes) == 2
        
        file_links = [node.get('LINK') for node in file_nodes]
        file_texts = [node.get('TEXT') for node in file_nodes]
        
        # File nodes should have proper names
        assert 'script.py' in file_texts
        assert 'module.py' in file_texts
        
        # File nodes should have proper links (relative paths)
        assert any('script.py' in link for link in file_links if link)
        assert any('module.py' in link for link in file_links if link)
    
    def test_alphabetical_word_grouping(self, generator, temp_output_file):
        """Test R-WORD-007: Group words alphabetically by first character when feasible."""
        word_results = {
            'apple': ['/test/file1.py'],
            'application': ['/test/file2.py'],
            'array': ['/test/file3.py'],
            'beta': ['/test/file4.py'],
            'binary': ['/test/file5.py'],
            'cache': ['/test/file6.py'],
        }
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the Word Index node
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None
        
        # With only 6 words, should be organized simply (no complex grouping needed)
        # Verify all words are present somewhere in the hierarchy
        all_node_texts = [node.get('TEXT') for node in word_index_node.findall('.//node')]
        
        assert 'apple' in all_node_texts
        assert 'application' in all_node_texts
        assert 'array' in all_node_texts
        assert 'beta' in all_node_texts
        assert 'binary' in all_node_texts
        assert 'cache' in all_node_texts
    
    def test_character_range_grouping(self, generator, temp_output_file):
        """Test R-WORD-008: Create character range nodes when single characters exceed 24 words."""
        word_results = {}
        
        # Create more than 24 words starting with different letters to force range grouping
        letters = 'abcdefghijklmnopqrstuvwxyz'
        for i, letter in enumerate(letters):
            word = f"{letter}word{i:02d}"
            word_results[word] = [f'/test/{letter}_file.py']
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the Word Index node
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None
        
        # Should have character range groups since 26 > 24
        direct_children = word_index_node.findall('./node')
        assert len(direct_children) <= 24
        
        # Look for range-style group names (e.g., "a-d", "e-h")
        group_names = [node.get('TEXT') for node in direct_children]
        
        # Should have some range groups or single character groups
        # The exact grouping strategy depends on implementation but should respect 24 limit
        range_groups = [name for name in group_names if '-' in name]
        single_char_groups = [name for name in group_names if len(name) == 1]
        word_groups = [name for name in group_names if name in word_results]
        
        # Total groups should not exceed 24
        assert len(group_names) <= 24
        
        # All original words should be findable somewhere in the hierarchy
        all_word_nodes = word_index_node.findall('.//node')
        all_texts = [node.get('TEXT') for node in all_word_nodes]
        
        for word in word_results.keys():
            assert word in all_texts, f"Word '{word}' not found in generated hierarchy"
    
    def test_flat_hierarchy_preference(self, generator, temp_output_file):
        """Test R-WORD-010: Keep hierarchy as flat as possible."""
        # Test with small number of words that should stay flat
        word_results = {
            'python': ['/test/file1.py'],
            'java': ['/test/file2.py'], 
            'cpp': ['/test/file3.py'],
            'javascript': ['/test/file4.py'],
        }
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the Word Index node
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None
        
        # With only 4 words, should be direct children (flat structure)
        # Count the depth - should be minimal
        max_depth = 0
        
        def calculate_max_depth(node, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            for child in node.findall('./node'):
                # Only count if this child represents a word, not a file
                child_text = child.get('TEXT')
                if child_text in word_results:
                    calculate_max_depth(child, current_depth + 1)
                elif not child.get('LINK'):  # Not a file link, so it's a grouping node
                    calculate_max_depth(child, current_depth + 1)
        
        calculate_max_depth(word_index_node)
        
        # Should be relatively flat - no deep nesting needed for 4 words
        assert max_depth <= 2, f"Hierarchy too deep ({max_depth}) for small word set"
    
    def test_word_node_ids_and_timestamps(self, generator, temp_output_file):
        """Test that word nodes have proper IDs and timestamps."""
        word_results = {
            'python': ['/test/file1.py'],
            'programming': ['/test/file2.py']
        }
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find all nodes in Word Index
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        all_nodes = word_index_node.findall('.//node')
        
        for node in all_nodes:
            # Every node should have ID
            assert node.get('ID') is not None
            assert node.get('ID') != ''
            
            # Every node should have timestamps
            assert node.get('CREATED') is not None
            assert node.get('MODIFIED') is not None
            
            # Timestamps should be in correct format (basic check)
            created = node.get('CREATED')
            modified = node.get('MODIFIED')
            assert 'T' in created  # ISO format includes T
            assert 'T' in modified
    
    def test_empty_word_results_handling(self, generator, temp_output_file):
        """Test proper handling of empty word results."""
        word_results = {}
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Word Index should not exist
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is None
    
    def test_single_word_handling(self, generator, temp_output_file):
        """Test handling of single word in results."""
        word_results = {
            'python': ['/test/file1.py', '/test/file2.py']
        }
        
        config = {}
        
        # Generate mindmap
        generator.create_mind_map(
            file_system_index={},
            keyword_entries=[],
            tag_results={},
            word_results=word_results,
            config=config
        )
        
        # Parse the generated XML
        tree = ET.parse(temp_output_file)
        root = tree.getroot()
        
        # Find the Word Index and verify structure
        word_index_node = root.find('.//node[@TEXT="Word Index"]')
        assert word_index_node is not None
        
        # Should have the python node
        python_node = word_index_node.find('.//node[@TEXT="python"]')
        assert python_node is not None
        
        # Python node should have file children
        file_nodes = python_node.findall('./node')
        assert len(file_nodes) == 2
        
        file_names = [node.get('TEXT') for node in file_nodes]
        assert 'file1.py' in file_names
        assert 'file2.py' in file_names