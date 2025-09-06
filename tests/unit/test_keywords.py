#!/usr/bin/env python3
"""
Unit tests for keyword file parsing and processing.

Tests the KeywordFileParser and KeywordProcessor classes.
"""

import pytest
from pathlib import Path
from io import StringIO

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from keywords import (
    KeywordEntry, KeywordFileParser, KeywordProcessor,
    load_keyword_files, create_sample_keyword_file
)


@pytest.mark.quick
class TestKeywordEntry:
    """Test cases for KeywordEntry class."""
    
    def test_entry_creation(self):
        """Test basic KeywordEntry creation."""
        entry = KeywordEntry(
            text="test keyword",
            level=1,
            is_leaf=True,
            line_number=5
        )
        
        assert entry.text == "test keyword"
        assert entry.level == 1
        assert entry.is_leaf is True
        assert entry.line_number == 5
        assert entry.children == []
        assert entry.parent is None
    
    def test_add_child(self):
        """Test adding child entries."""
        parent = KeywordEntry("parent", 0, False)
        child = KeywordEntry("child", 1, True)
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert child.parent == parent
    
    def test_get_search_sequences_leaf_single(self):
        """Test getting search sequences from single-term leaf."""
        entry = KeywordEntry("keyword", 1, True)
        
        sequences = entry.get_search_sequences()
        
        assert len(sequences) == 1
        assert sequences[0] == ["keyword"]
    
    def test_get_search_sequences_leaf_multiple(self):
        """Test getting search sequences from multi-term leaf."""
        entry = KeywordEntry("function:async:definition", 1, True)
        
        sequences = entry.get_search_sequences()
        
        assert len(sequences) == 1
        assert sequences[0] == ["function", "async", "definition"]
    
    def test_get_search_sequences_organizational(self):
        """Test getting search sequences from organizational entry."""
        parent = KeywordEntry("Programming", 0, False)
        child1 = KeywordEntry("function:definition", 1, True)
        child2 = KeywordEntry("class:inheritance", 1, True)
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        sequences = parent.get_search_sequences()
        
        assert len(sequences) == 2
        assert ["function", "definition"] in sequences
        assert ["class", "inheritance"] in sequences
    
    def test_get_display_name_single(self):
        """Test display name for single keyword."""
        entry = KeywordEntry("keyword", 1, True)
        
        assert entry.get_display_name() == "keyword"
    
    def test_get_display_name_sequence(self):
        """Test display name for keyword sequence."""
        entry = KeywordEntry("function:async:definition", 1, True)
        
        assert entry.get_display_name() == "function → async → definition"


@pytest.mark.quick
class TestKeywordFileParser:
    """Test cases for KeywordFileParser class."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = KeywordFileParser()
        assert parser.tab_size == 1
        
        parser = KeywordFileParser(tab_size=4)
        assert parser.tab_size == 4
    
    def test_calculate_indentation_level_tabs(self):
        """Test indentation calculation with tabs."""
        parser = KeywordFileParser()
        
        assert parser._calculate_indentation_level("no indent") == 0
        assert parser._calculate_indentation_level("\tone tab") == 1
        assert parser._calculate_indentation_level("\t\ttwo tabs") == 2
        assert parser._calculate_indentation_level("\t\t\tthree tabs") == 3
    
    def test_calculate_indentation_level_spaces(self):
        """Test indentation calculation with spaces."""
        parser = KeywordFileParser()
        
        assert parser._calculate_indentation_level("    four spaces") == 1  # 4 spaces = 1 tab
        assert parser._calculate_indentation_level("        eight spaces") == 2  # 8 spaces = 2 tabs
    
    def test_calculate_indentation_level_mixed(self):
        """Test indentation calculation with mixed tabs and spaces."""
        parser = KeywordFileParser()
        
        # 1 tab + 2 spaces = 1.5 tabs -> 1 (int conversion)
        assert parser._calculate_indentation_level("\t  mixed") == 1
    
    def test_parse_simple_structure(self):
        """Test parsing simple keyword structure."""
        parser = KeywordFileParser()
        lines = [
            "Category 1\n",
            "\tkeyword1\n",
            "\tkeyword2\n",
            "Category 2\n",
            "\tkeyword3\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 2
        assert entries[0].text == "Category 1"
        assert entries[0].is_leaf is False
        assert len(entries[0].children) == 2
        assert entries[0].children[0].text == "keyword1"
        assert entries[0].children[1].text == "keyword2"
    
    def test_parse_nested_structure(self):
        """Test parsing nested keyword structure."""
        parser = KeywordFileParser()
        lines = [
            "Root Category\n",
            "\tSubcategory 1\n",
            "\t\tkeyword1\n",
            "\t\tkeyword2\n",
            "\tSubcategory 2\n",
            "\t\tkeyword3\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        root = entries[0]
        assert root.text == "Root Category"
        assert len(root.children) == 2
        
        sub1 = root.children[0]
        assert sub1.text == "Subcategory 1"
        assert len(sub1.children) == 2
        assert sub1.children[0].text == "keyword1"
        assert sub1.children[1].text == "keyword2"
    
    def test_parse_with_comments(self):
        """Test parsing with comment lines."""
        parser = KeywordFileParser()
        lines = [
            "# This is a comment\n",
            "Category\n",
            "\t# Another comment\n",
            "\tkeyword1\n",
            "# Final comment\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        assert entries[0].text == "Category"
        assert len(entries[0].children) == 1
        assert entries[0].children[0].text == "keyword1"
    
    def test_parse_with_empty_lines(self):
        """Test parsing with empty lines."""
        parser = KeywordFileParser()
        lines = [
            "\n",
            "Category\n",
            "\n",
            "\tkeyword1\n",
            "\n",
            "\tkeyword2\n",
            "\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        assert entries[0].text == "Category"
        assert len(entries[0].children) == 2
    
    def test_parse_colon_sequences(self):
        """Test parsing colon-separated sequences."""
        parser = KeywordFileParser()
        lines = [
            "Programming\n",
            "\tfunction:definition\n",
            "\tclass:inheritance:multiple\n"
        ]
        
        entries = parser.parse_lines(lines)
        
        assert len(entries) == 1
        programming = entries[0]
        assert len(programming.children) == 2
        
        sequences = programming.get_search_sequences()
        assert ["function", "definition"] in sequences
        assert ["class", "inheritance", "multiple"] in sequences
    
    def test_parse_file_not_exists(self):
        """Test parsing non-existent file."""
        parser = KeywordFileParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/file.txt")
    
    def test_parse_file_from_disk(self, temp_dir):
        """Test parsing actual file from disk."""
        parser = KeywordFileParser()
        
        keyword_file = temp_dir / "test_keywords.txt"
        keyword_file.write_text("""# Test keywords
Programming
\tFunctions
\t\tfunction:definition
\tClasses
\t\tclass:creation
""")
        
        entries = parser.parse_file(str(keyword_file))
        
        assert len(entries) == 1
        assert entries[0].text == "Programming"
        assert len(entries[0].children) == 2
    
    def test_validate_structure_valid(self):
        """Test structure validation with valid structure."""
        parser = KeywordFileParser()
        
        entry = KeywordEntry("Category", 0, False, line_number=1)
        child = KeywordEntry("keyword", 1, True, line_number=2)
        entry.add_child(child)
        
        warnings = parser.validate_structure([entry])
        
        assert len(warnings) == 0
    
    def test_validate_structure_empty_entry(self):
        """Test structure validation with empty entry."""
        parser = KeywordFileParser()
        
        entry = KeywordEntry("", 0, True, line_number=1)
        
        warnings = parser.validate_structure([entry])
        
        assert len(warnings) == 1
        assert "Empty entry" in warnings[0]
    
    def test_validate_structure_colon_in_nonleaf(self):
        """Test structure validation with colon in non-leaf entry."""
        parser = KeywordFileParser()
        
        entry = KeywordEntry("category:invalid", 0, False, line_number=1)
        child = KeywordEntry("keyword", 1, True, line_number=2)
        entry.add_child(child)
        
        warnings = parser.validate_structure([entry])
        
        assert len(warnings) == 1
        assert "Non-leaf entry contains colon" in warnings[0]
    
    def test_validate_structure_deep_nesting(self):
        """Test structure validation with very deep nesting."""
        parser = KeywordFileParser()
        
        # Create deeply nested structure
        current = KeywordEntry("Level0", 0, False, line_number=1)
        entries = [current]
        
        for i in range(1, 8):  # Create 8 levels deep
            child = KeywordEntry(f"Level{i}", i, False, line_number=i+1)
            current.add_child(child)
            current = child
        
        # Make the last one a leaf
        current.is_leaf = True
        
        warnings = parser.validate_structure(entries)
        
        assert len(warnings) == 1
        assert "Very deep nesting" in warnings[0]


@pytest.mark.quick
class TestKeywordProcessor:
    """Test cases for KeywordProcessor class."""
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = KeywordProcessor()
        assert processor.debug is False
    
    def test_set_debug(self):
        """Test debug mode setting."""
        processor = KeywordProcessor()
        processor.set_debug(True)
        assert processor.debug is True
    
    def test_extract_all_search_sequences(self):
        """Test extracting all search sequences by category."""
        processor = KeywordProcessor()
        
        # Create test entries
        cat1 = KeywordEntry("Programming", 0, False)
        cat1.add_child(KeywordEntry("function:definition", 1, True))
        cat1.add_child(KeywordEntry("class:creation", 1, True))
        
        cat2 = KeywordEntry("Documentation", 0, False)
        cat2.add_child(KeywordEntry("api:reference", 1, True))
        
        entries = [cat1, cat2]
        
        sequences_by_category = processor.extract_all_search_sequences(entries)
        
        assert len(sequences_by_category) == 2
        assert "Programming" in sequences_by_category
        assert "Documentation" in sequences_by_category
        
        programming_sequences = sequences_by_category["Programming"]
        assert len(programming_sequences) == 2
        assert ["function", "definition"] in programming_sequences
        assert ["class", "creation"] in programming_sequences
        
        doc_sequences = sequences_by_category["Documentation"]
        assert len(doc_sequences) == 1
        assert ["api", "reference"] in doc_sequences
    
    def test_flatten_search_sequences(self):
        """Test flattening search sequences."""
        processor = KeywordProcessor()
        
        cat1 = KeywordEntry("Category1", 0, False)
        cat1.add_child(KeywordEntry("keyword1", 1, True))
        cat1.add_child(KeywordEntry("keyword2:sequence", 1, True))
        
        cat2 = KeywordEntry("Category2", 0, False)
        cat2.add_child(KeywordEntry("keyword3", 1, True))
        
        entries = [cat1, cat2]
        
        flattened = processor.flatten_search_sequences(entries)
        
        assert len(flattened) == 3
        assert ["keyword1"] in flattened
        assert ["keyword2", "sequence"] in flattened
        assert ["keyword3"] in flattened
    
    def test_build_organizational_hierarchy(self):
        """Test building organizational hierarchy."""
        processor = KeywordProcessor()
        
        root = KeywordEntry("Programming", 0, False)
        functions = KeywordEntry("Functions", 1, False)
        functions.add_child(KeywordEntry("function:definition", 2, True))
        root.add_child(functions)
        
        entries = [root]
        
        hierarchy = processor.build_organizational_hierarchy(entries)
        
        assert "Programming" in hierarchy
        prog_entry = hierarchy["Programming"]
        assert prog_entry["text"] == "Programming"
        assert prog_entry["is_leaf"] is False
        assert "children" in prog_entry
        
        assert "Functions" in prog_entry["children"]
        func_entry = prog_entry["children"]["Functions"]
        assert func_entry["is_leaf"] is False
        
        # Check leaf entry
        func_def = func_entry["children"]["function:definition"]
        assert func_def["is_leaf"] is True
        assert func_def["search_sequence"] == ["function", "definition"]
        assert func_def["display_name"] == "function → definition"


@pytest.mark.quick
class TestKeywordUtilityFunctions:
    """Test cases for keyword utility functions."""
    
    def test_load_keyword_files_single(self, temp_dir):
        """Test loading single keyword file."""
        keyword_file = temp_dir / "keywords.txt"
        keyword_file.write_text("""Programming
\tFunctions
\t\tfunction:definition
""")
        
        entries, warnings = load_keyword_files([str(keyword_file)], debug=False)
        
        assert len(entries) == 1
        assert entries[0].text == "Programming"
        assert len(warnings) == 0
    
    def test_load_keyword_files_multiple(self, temp_dir):
        """Test loading multiple keyword files."""
        file1 = temp_dir / "keywords1.txt"
        file1.write_text("Category1\n\tkeyword1")
        
        file2 = temp_dir / "keywords2.txt"
        file2.write_text("Category2\n\tkeyword2")
        
        entries, warnings = load_keyword_files([str(file1), str(file2)], debug=False)
        
        assert len(entries) == 2
        assert entries[0].text == "Category1"
        assert entries[1].text == "Category2"
        assert len(warnings) == 0
    
    def test_load_keyword_files_with_errors(self, temp_dir):
        """Test loading keyword files with errors."""
        # Create valid file
        valid_file = temp_dir / "valid.txt"
        valid_file.write_text("Category\n\tkeyword")
        
        # Non-existent file
        invalid_file = temp_dir / "nonexistent.txt"
        
        entries, warnings = load_keyword_files([str(valid_file), str(invalid_file)], debug=False)
        
        # Should load valid entries and report warnings
        assert len(entries) == 1
        assert entries[0].text == "Category"
        assert len(warnings) == 1
        assert "Error loading" in warnings[0]
    
    def test_create_sample_keyword_file(self, temp_dir):
        """Test creating sample keyword file."""
        sample_file = temp_dir / "sample.txt"
        
        create_sample_keyword_file(str(sample_file))
        
        assert sample_file.exists()
        content = sample_file.read_text()
        
        # Should contain expected structure
        assert "Programming Concepts" in content
        assert "\tFunctions" in content
        assert "\t\tfunction:definition" in content
        assert "# Sample keyword file" in content


@pytest.mark.quick
class TestKeywordIntegration:
    """Integration tests for keyword functionality."""
    
    def test_full_keyword_processing_workflow(self, temp_dir):
        """Test complete keyword processing workflow."""
        # Create complex keyword file
        keyword_file = temp_dir / "complex_keywords.txt"
        keyword_file.write_text("""# Complex keyword structure
Programming Concepts
\tFunctions
\t\tfunction:definition
\t\tasync:function:implementation
\tClasses
\t\tclass:inheritance:single
\t\tclass:inheritance:multiple
\t\tinterface:implementation

Documentation
\tAPI Reference
\t\tapi:endpoint:GET
\t\tapi:endpoint:POST
\tUser Guides
\t\ttutorial:beginner:setup
\t\tguide:advanced:configuration
""")
        
        # Parse file
        parser = KeywordFileParser()
        entries = parser.parse_file(str(keyword_file))
        
        # Validate structure
        warnings = parser.validate_structure(entries)
        assert len(warnings) == 0
        
        # Process entries
        processor = KeywordProcessor()
        sequences_by_category = processor.extract_all_search_sequences(entries)
        
        # Verify structure
        assert len(sequences_by_category) == 2
        assert "Programming Concepts" in sequences_by_category
        assert "Documentation" in sequences_by_category
        
        # Check programming sequences
        prog_sequences = sequences_by_category["Programming Concepts"]
        expected_sequences = [
            ["function", "definition"],
            ["async", "function", "implementation"],
            ["class", "inheritance", "single"],
            ["class", "inheritance", "multiple"],
            ["interface", "implementation"]
        ]
        
        for expected in expected_sequences:
            assert expected in prog_sequences
        
        # Check documentation sequences
        doc_sequences = sequences_by_category["Documentation"]
        expected_doc_sequences = [
            ["api", "endpoint", "GET"],
            ["api", "endpoint", "POST"],
            ["tutorial", "beginner", "setup"],
            ["guide", "advanced", "configuration"]
        ]
        
        for expected in expected_doc_sequences:
            assert expected in doc_sequences
        
        # Test flattening
        all_sequences = processor.flatten_search_sequences(entries)
        assert len(all_sequences) == 9  # Total of all sequences
        
        # Test hierarchy building
        hierarchy = processor.build_organizational_hierarchy(entries)
        assert len(hierarchy) == 2
        
        # Check nested structure in hierarchy
        prog_hierarchy = hierarchy["Programming Concepts"]
        assert "Functions" in prog_hierarchy["children"]
        functions = prog_hierarchy["children"]["Functions"]
        
        assert "function:definition" in functions["children"]
        func_def = functions["children"]["function:definition"]
        assert func_def["is_leaf"] is True
        assert func_def["search_sequence"] == ["function", "definition"]