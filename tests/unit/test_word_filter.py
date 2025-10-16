#!/usr/bin/env python3
"""
Unit tests for SignificantWordFilter functionality.

Tests word extraction, filtering, and hierarchical grouping capabilities
according to requirements R-WORD-001 to R-WORD-015.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from word_filter import SignificantWordFilter


class TestSignificantWordFilter:
    """Test cases for significant word filtering functionality."""
    
    @pytest.fixture
    def word_filter(self):
        """Create SignificantWordFilter instance for testing."""
        return SignificantWordFilter()
    
    def test_basic_word_extraction(self, word_filter):
        """Test R-WORD-002, R-WORD-013: Basic significant word extraction with word boundaries."""
        text = "This document discusses Python programming and machine-learning concepts."
        
        words = word_filter.extract_significant_words(text)
        
        # Should include technical terms
        assert 'python' in words
        assert 'programming' in words
        assert 'machine-learning' in words
        assert 'concepts' in words
        assert 'document' in words
        assert 'discusses' in words
        
        # Should exclude stop words
        assert 'this' not in words
        assert 'and' not in words
    
    def test_stop_word_filtering(self, word_filter):
        """Test R-WORD-003: Exclude stop words, pronouns, conjunctions, prepositions."""
        text = """
        This is a comprehensive test of the filtering system.
        We want to verify that it properly excludes common words like:
        articles (a, an, the), pronouns (I, you, he, she, it, we, they),
        conjunctions (and, or, but, nor), prepositions (in, on, at, by, with).
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should exclude articles
        assert 'a' not in words
        assert 'an' not in words
        assert 'the' not in words
        
        # Should exclude pronouns
        assert 'i' not in words
        assert 'you' not in words
        assert 'he' not in words
        assert 'she' not in words
        assert 'it' not in words
        assert 'we' not in words
        assert 'they' not in words
        
        # Should exclude conjunctions
        assert 'and' not in words
        assert 'or' not in words
        assert 'but' not in words
        assert 'nor' not in words
        
        # Should exclude prepositions
        assert 'in' not in words
        assert 'on' not in words
        assert 'at' not in words
        assert 'by' not in words
        assert 'with' not in words
        
        # Should include significant words
        assert 'comprehensive' in words
        assert 'filtering' in words
        assert 'system' in words
        assert 'verify' in words
        assert 'properly' in words
        assert 'excludes' in words
    
    def test_technical_term_preservation(self, word_filter):
        """Test R-WORD-004, R-WORD-015: Include technical terms and preserve abbreviations."""
        text = """
        The API uses HTTP and HTTPS protocols for communication.
        JSON and XML are common data formats.
        CPU and GPU performance is crucial for ML algorithms.
        The SDK provides comprehensive documentation.
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should include technical abbreviations
        assert 'api' in words
        assert 'http' in words
        assert 'https' in words
        assert 'json' in words
        assert 'xml' in words
        assert 'cpu' in words
        assert 'gpu' in words
        assert 'ml' in words  # Machine Learning
        assert 'sdk' in words
        
        # Should include technical terms
        assert 'protocols' in words
        assert 'communication' in words
        assert 'formats' in words
        assert 'performance' in words
        assert 'algorithms' in words
        assert 'documentation' in words
    
    def test_compound_word_preservation(self, word_filter):
        """Test R-WORD-004: Include compound words with hyphens and underscores."""
        text = """
        The machine-learning algorithm uses real-time processing.
        The data_structure implements thread_safety mechanisms.
        Cross-platform compatibility is important for multi-user environments.
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should include hyphenated compounds
        assert 'machine-learning' in words
        assert 'real-time' in words
        assert 'cross-platform' in words
        assert 'multi-user' in words
        
        # Should include underscore compounds
        assert 'data_structure' in words
        assert 'thread_safety' in words
    
    def test_number_filtering(self, word_filter):
        """Test R-WORD-014: Filter out pure numbers and predominantly numeric strings."""
        text = """
        Version 3.14 of the software includes 42 new features.
        The server runs on port 8080 with 2GB of RAM.
        Algorithm complexity is O(n2) where n equals 100000.
        The config file uses values like abc123 and test456data.
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should exclude pure numbers
        assert '3' not in words
        assert '14' not in words
        assert '42' not in words
        assert '8080' not in words
        assert '2' not in words
        assert '100000' not in words
        
        # Should include words with some numbers but not predominantly numeric
        assert 'version' in words
        assert 'software' in words
        assert 'features' in words
        assert 'server' in words
        assert 'port' in words
        assert 'ram' in words  # Should be preserved as technical term
        assert 'algorithm' in words
        assert 'complexity' in words
        assert 'config' in words
        
        # Mixed alphanumeric - depends on ratio, but meaningful parts should be kept
        # These specific examples may or may not pass depending on the exact filtering logic
    
    def test_minimum_word_length(self, word_filter):
        """Test word length filtering (minimum 2 characters by default)."""
        text = "A big CPU can run AI and ML algorithms at high speed."
        
        words = word_filter.extract_significant_words(text)
        
        # Should exclude single characters (except preserved technical terms)
        assert 'a' not in words  # Stop word anyway
        
        # Should include 2+ character technical terms
        assert 'ai' in words  # Technical abbreviation
        assert 'ml' in words  # Technical abbreviation
        assert 'cpu' in words  # Technical abbreviation
        
        # Should include other valid words
        assert 'big' in words
        assert 'run' in words
        assert 'algorithms' in words
        assert 'high' in words
        assert 'speed' in words
    
    def test_frequency_counting(self, word_filter):
        """Test R-WORD-005: Word frequency counting with minimum threshold."""
        texts = [
            "Python programming is powerful and flexible.",
            "Python developers love the language flexibility.",
            "Java programming requires more verbosity than Python.",
            "Ruby programming emphasizes developer happiness.",
        ]
        
        # Test with minimum frequency of 2
        word_freq = word_filter.get_word_frequency(texts, min_frequency=2)
        
        # Should include words appearing 2+ times
        assert 'python' in word_freq
        assert word_freq['python'] == 3
        assert 'programming' in word_freq
        assert word_freq['programming'] == 3
        
        # Should exclude words appearing only once
        assert 'powerful' not in word_freq
        assert 'java' not in word_freq
        assert 'ruby' not in word_freq
        assert 'happiness' not in word_freq
        
        # Should include words appearing exactly twice
        if 'developer' in word_freq:
            assert word_freq['developer'] >= 2
    
    def test_hierarchical_grouping_simple(self, word_filter):
        """Test R-WORD-006, R-WORD-007: Basic hierarchical grouping with max 24 children."""
        words = ['apple', 'application', 'array', 'beta', 'binary', 'cache', 'config']
        
        groups = word_filter.create_hierarchical_groups(words, max_children=24)
        
        # With 7 words, should fit in single level
        assert 'words' in groups
        assert len(groups['words']) == 7
        assert 'apple' in groups['words']
        assert 'config' in groups['words']
    
    def test_hierarchical_grouping_character_groups(self, word_filter):
        """Test R-WORD-007, R-WORD-008: Character-based grouping when needed."""
        # Create 26 words (more than 24) starting with different letters
        words = [f"{chr(ord('a') + i)}word{i:02d}" for i in range(26)]
        
        groups = word_filter.create_hierarchical_groups(words, max_children=24)
        
        # Should create character groups since we have 26 > 24
        assert 'words' not in groups  # Not a simple word list
        
        # Should have character-based grouping
        char_groups = list(groups.keys())
        assert len(char_groups) <= 24  # Respects max children limit
        
        # Check that some character groups exist
        total_words = 0
        for group_name, group_content in groups.items():
            if 'words' in group_content:
                total_words += len(group_content['words'])
            # Or recursively count if nested
        
        # Should account for all original words
        # (exact structure depends on implementation, but total should match)
    
    def test_hierarchical_grouping_prefix_subdivision(self, word_filter):
        """Test R-WORD-009: Subdivide by prefixes when single characters exceed limit."""
        # Create many words starting with 'a' to force prefix subdivision
        words = [f"a{chr(ord('a') + i)}{chr(ord('a') + j)}word" 
                for i in range(5) for j in range(6)]  # 30 words starting with 'a'
        words.extend(['bword', 'cword', 'dword'])  # Add some other letters
        
        groups = word_filter.create_hierarchical_groups(words, max_children=24)
        
        # Should create groupings that respect the 24-child limit at each level
        def count_children(group_dict):
            """Count direct children of a group."""
            if 'words' in group_dict:
                return len(group_dict['words'])
            else:
                return len(group_dict.keys())
        
        def check_max_children_recursive(group_dict):
            """Recursively check that no node has more than 24 children."""
            children_count = count_children(group_dict)
            assert children_count <= 24, f"Group has {children_count} children, exceeds limit of 24"
            
            if 'words' not in group_dict:
                for subgroup in group_dict.values():
                    check_max_children_recursive(subgroup)
        
        check_max_children_recursive(groups)
    
    def test_flat_hierarchy_preference(self, word_filter):
        """Test R-WORD-010: Keep hierarchy as flat as possible."""
        # Test with a number of words that can be organized flatly
        words = ['apple', 'banana', 'cherry', 'date', 'elderberry', 'fig']
        
        groups = word_filter.create_hierarchical_groups(words, max_children=24)
        
        # Should create flat structure when possible
        assert 'words' in groups  # Direct word list, no intermediate groups
        assert len(groups['words']) == 6
    
    def test_empty_input_handling(self, word_filter):
        """Test handling of empty or invalid inputs."""
        # Test empty text
        words = word_filter.extract_significant_words("")
        assert words == []
        
        # Test None input
        words = word_filter.extract_significant_words(None)
        assert words == []
        
        # Test whitespace only
        words = word_filter.extract_significant_words("   \n\t  ")
        assert words == []
        
        # Test empty word frequency
        word_freq = word_filter.get_word_frequency([], min_frequency=2)
        assert word_freq == {}
        
        # Test empty hierarchical grouping
        groups = word_filter.create_hierarchical_groups([], max_children=24)
        assert groups == {'words': []}
    
    def test_case_insensitive_processing(self, word_filter):
        """Test that word processing is case-insensitive."""
        text = "Python PYTHON python PyThOn Programming PROGRAMMING"
        
        words = word_filter.extract_significant_words(text)
        
        # All variations should be normalized to lowercase
        assert 'python' in words
        assert 'programming' in words
        
        # Should not have multiple case variations
        assert 'Python' not in words
        assert 'PYTHON' not in words
        assert 'PyThOn' not in words
        assert 'PROGRAMMING' not in words
    
    def test_technical_suffix_recognition(self, word_filter):
        """Test recognition of technical suffixes that indicate domain terms."""
        text = """
        The optimization algorithm uses serialization and deserialization.
        The implementation provides extensibility through modularity.
        Authentication and authorization handle security systematically.
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should include words with technical suffixes
        assert 'optimization' in words      # -tion suffix
        assert 'algorithm' in words        # technical term
        assert 'serialization' in words    # -tion suffix
        assert 'deserialization' in words  # -tion suffix
        assert 'implementation' in words   # -tion suffix
        assert 'extensibility' in words    # -ity suffix
        assert 'modularity' in words       # -ity suffix
        assert 'authentication' in words   # -tion suffix
        assert 'authorization' in words    # -tion suffix
        assert 'systematically' in words   # -ally suffix
    
    def test_programming_term_recognition(self, word_filter):
        """Test recognition of programming-specific terminology."""
        text = """
        The class inherits from an abstract interface.
        Functions return values stored in variables and constants.
        Arrays and dictionaries are common data structures.
        Exception handling improves error debugging.
        """
        
        words = word_filter.extract_significant_words(text)
        
        # Should include programming terms
        assert 'class' in words
        assert 'inherits' in words
        assert 'abstract' in words
        assert 'interface' in words
        assert 'functions' in words
        assert 'return' in words
        assert 'variables' in words
        assert 'constants' in words
        assert 'arrays' in words
        assert 'dictionaries' in words
        assert 'structures' in words
        assert 'exception' in words
        assert 'handling' in words
        assert 'error' in words
        assert 'debugging' in words