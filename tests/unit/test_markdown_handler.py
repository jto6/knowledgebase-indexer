#!/usr/bin/env python3
"""
Unit tests for MarkdownHandler tag extraction functionality.

Tests the markdown-specific tag processing requirements R-MARKDOWN-TAG-001 to R-MARKDOWN-TAG-007.
"""

import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.markdown_handler import MarkdownHandler


@pytest.fixture
def markdown_handler():
    """Create MarkdownHandler instance for testing."""
    config = {
        'extensions': ['.md', '.markdown'],
        'hierarchy_config': {},
        'search_config': {},
        'link_config': {}
    }
    return MarkdownHandler(config)


@pytest.fixture
def temp_markdown_file():
    """Create temporary markdown file for testing."""
    fd, path = tempfile.mkstemp(suffix='.md')
    yield path
    os.close(fd)
    os.unlink(path)


class TestMarkdownTagExtraction:
    """Test cases for markdown tag extraction functionality."""
    
    def test_hashtag_extraction(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-001: Extract hashtag-style tags."""
        content = """# Test Document

This document discusses #python programming and #machine-learning concepts.
We also cover #data-science and #AI topics.

Some text with #web_development and #javascript.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        # Should return Dict[str, List[tuple]] format
        assert isinstance(result, dict)
        
        expected_tags = {'python', 'machine-learning', 'data-science', 
                        'AI', 'web_development', 'javascript'}
        
        # Check that all expected tags are present
        for tag in expected_tags:
            assert tag in result
            assert isinstance(result[tag], list)
            assert len(result[tag]) == 1
            # Each tuple should be (file_path, node_id, node_text)
            file_path, node_id, node_text = result[tag][0]
            assert file_path == temp_markdown_file
            assert node_id == ''  # Empty for file-level tags
            assert node_text == Path(temp_markdown_file).name

    def test_yaml_frontmatter_tags_list_format(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-002, R-MARKDOWN-TAG-003: Extract YAML frontmatter tags in list format."""
        content = """---
title: Test Document
tags: [python, machine-learning, data-science]
author: Test Author
---

# Content

This is the main content.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        expected_tags = {'python', 'machine-learning', 'data-science'}
        
        assert len(result) == len(expected_tags)
        for tag in expected_tags:
            assert tag in result
            assert len(result[tag]) == 1
            file_path, node_id, node_text = result[tag][0]
            assert file_path == temp_markdown_file
            assert node_id == ''
            assert node_text == Path(temp_markdown_file).name

    def test_yaml_frontmatter_tags_comma_separated(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-002, R-MARKDOWN-TAG-004: Extract YAML frontmatter tags in comma-separated format."""
        content = """---
title: Test Document
tags: python, machine-learning, data-science, web-development
---

# Content

This is the main content.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        expected_tags = {'python', 'machine-learning', 'data-science', 'web-development'}
        
        assert len(result) == len(expected_tags)
        for tag in expected_tags:
            assert tag in result

    def test_yaml_frontmatter_single_tag_field(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-002: Extract from single 'tag:' field."""
        content = """---
title: Test Document
tag: python
---

# Content

This is the main content.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        assert len(result) == 1
        assert 'python' in result

    def test_yaml_tags_with_quotes_and_whitespace(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-005: Strip quotes and whitespace from YAML tag values."""
        content = """---
title: Test Document
tags: ["python", 'machine-learning', "  data-science  ", web-development  ]
---

# Content
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        expected_tags = {'python', 'machine-learning', 'data-science', 'web-development'}
        
        assert len(result) == len(expected_tags)
        for tag in expected_tags:
            assert tag in result

    def test_combined_hashtag_and_frontmatter_tags(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-006: Combine hashtag and frontmatter tags into unified tag list."""
        content = """---
title: Test Document
tags: [python, data-science]
---

# Content

This document also discusses #machine-learning and #AI concepts.
We have some overlap with #python as well.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        # Should combine both sources
        expected_tags = {'python', 'data-science', 'machine-learning', 'AI'}
        
        for tag in expected_tags:
            assert tag in result

    def test_file_level_tag_association(self, markdown_handler, temp_markdown_file):
        """Test R-MARKDOWN-TAG-007: Associate tags with file-level context for linking."""
        content = """---
tags: [test-tag]
---

# Test

Content with #hashtag.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        # Verify file-level association
        for tag_name, tag_entries in result.items():
            assert len(tag_entries) == 1
            file_path, node_id, node_text = tag_entries[0]
            
            # Should be associated with the file
            assert file_path == temp_markdown_file
            # File-level tags have empty node_id
            assert node_id == ''
            # Node text should be filename for display
            assert node_text == Path(temp_markdown_file).name

    def test_no_tags_present(self, markdown_handler, temp_markdown_file):
        """Test behavior when no tags are present."""
        content = """# Test Document

This document has no tags at all.
Just regular content.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_empty_frontmatter_tags(self, markdown_handler, temp_markdown_file):
        """Test behavior with empty frontmatter tags."""
        content = """---
title: Test
tags: []
---

# Content
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        assert len(result) == 0

    def test_malformed_yaml_frontmatter(self, markdown_handler, temp_markdown_file):
        """Test behavior with malformed YAML frontmatter."""
        content = """---
title: Test
tags: [unclosed list
---

# Content with #hashtag
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        # Should still extract hashtags even if YAML is malformed
        assert 'hashtag' in result

    def test_case_insensitive_yaml_fields(self, markdown_handler, temp_markdown_file):
        """Test that YAML field matching is case insensitive."""
        content = """---
title: Test
Tags: [python, javascript]
TAG: machine-learning
---

# Content
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        expected_tags = {'python', 'javascript', 'machine-learning'}
        
        for tag in expected_tags:
            assert tag in result

    def test_duplicate_tags_handling(self, markdown_handler, temp_markdown_file):
        """Test that duplicate tags are handled correctly."""
        content = """---
tags: [python, javascript, python]
---

# Content

Discussion about #python and #javascript.
Also more about #python programming.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        result = markdown_handler.extract_tags(temp_markdown_file)
        
        # Each tag should appear only once in the result
        assert 'python' in result
        assert 'javascript' in result
        
        # Each tag should have only one entry (file-level)
        assert len(result['python']) == 1
        assert len(result['javascript']) == 1

    def test_error_handling_nonexistent_file(self, markdown_handler):
        """Test error handling for non-existent files."""
        result = markdown_handler.extract_tags('/nonexistent/file.md')
        
        # Should return empty dict without crashing
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_error_handling_unreadable_file(self, markdown_handler, temp_markdown_file):
        """Test error handling for unreadable files."""
        # Create file then make it unreadable
        with open(temp_markdown_file, 'w') as f:
            f.write("# Test")
        
        os.chmod(temp_markdown_file, 0o000)
        
        try:
            result = markdown_handler.extract_tags(temp_markdown_file)
            # Should return empty dict without crashing
            assert isinstance(result, dict)
            assert len(result) == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_markdown_file, 0o644)