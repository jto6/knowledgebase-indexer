#!/usr/bin/env python3
"""
Unit tests for markdown content search functionality.

Tests that verify all types of markdown content (headings, body text, lists, 
code blocks, etc.) are properly searchable through the get_node_content() method.
"""

import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.markdown_handler import MarkdownHandler
from core_handlers import create_word_boundary_pattern


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


class TestMarkdownContentSearch:
    """Test cases for comprehensive markdown content searching."""
    
    def test_heading_content_includes_section_text(self, markdown_handler, temp_markdown_file):
        """Test that heading nodes include all content until next heading."""
        content = """# Main Heading

This is paragraph content under main heading.
It should be searchable along with the heading text.

Another paragraph with keyword *searchterm* in emphasis.

## Subheading

This is under the subheading.
The main heading node should NOT include this text.

# Another Main Heading

This starts a new section.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        # Get root nodes
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Should have 2 main headings
        main_headings = [node for node in root_nodes if node.node_type == 'heading' and node.metadata.get('heading_level') == 1]
        assert len(main_headings) == 2
        
        # Test first main heading content
        first_heading = main_headings[0]
        heading_content = markdown_handler.get_node_content(first_heading)
        
        # Should include heading text
        assert "Main Heading" in heading_content
        # Should include paragraph content directly under this heading
        assert "This is paragraph content under main heading" in heading_content
        assert "Another paragraph with keyword" in heading_content
        assert "searchterm" in heading_content
        
        # Should NOT include subheading content (now that hierarchy works correctly)
        assert "This is under the subheading" not in heading_content
        assert "Another Main Heading" not in heading_content
        
        # Verify the subheading exists as a child
        subheadings = [node for node in first_heading.children if node.node_type == 'heading']
        assert len(subheadings) >= 1
        subheading_content = markdown_handler.get_node_content(subheadings[0])
        assert "This is under the subheading" in subheading_content

    def test_search_finds_content_in_heading_sections(self, markdown_handler, temp_markdown_file):
        """Test that search finds keywords in section content, not just headings."""
        content = """# Programming Guide

This section covers Python programming concepts.

Python is a versatile language with many features.
Functions are defined using the def keyword.

## Advanced Topics

More advanced Python concepts here.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        # Get root nodes
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        main_heading = root_nodes[0]
        
        # Test search for "Python" - should find it in section content
        pattern = create_word_boundary_pattern("Python")
        results = markdown_handler.search_in_node_subtree(main_heading, pattern, include_descendants=True)
        
        assert len(results) >= 1
        assert any("Programming Guide" in markdown_handler.get_node_content(result) for result in results)
        
        # Test search for "functions" - should find it in section content
        pattern = create_word_boundary_pattern("Functions")
        results = markdown_handler.search_in_node_subtree(main_heading, pattern, include_descendants=True)
        
        assert len(results) >= 1

    def test_list_item_content_searchable(self, markdown_handler, temp_markdown_file):
        """Test that list items are searchable."""
        content = """# Features

## Key Features

- Authentication system with JWT tokens
- Database integration using SQLAlchemy
- RESTful API endpoints
  - User management endpoint
  - Data processing endpoint
- Comprehensive logging framework
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        # Get all nodes
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Search for "Authentication" - should find it in list item
        pattern = create_word_boundary_pattern("Authentication")
        all_results = []
        for root in root_nodes:
            results = markdown_handler.search_in_node_subtree(root, pattern, include_descendants=True)
            all_results.extend(results)
        
        assert len(all_results) >= 1
        
        # Should find list item nodes (they are now separate hierarchical nodes)
        list_results = [r for r in all_results if r.node_type == 'list_item']
        assert len(list_results) >= 1
        
        # Verify the authentication list item exists
        auth_items = [r for r in list_results if "Authentication system" in markdown_handler.get_node_content(r)]
        assert len(auth_items) >= 1

    def test_nested_list_content_searchable(self, markdown_handler, temp_markdown_file):
        """Test that nested list items are searchable."""
        content = """# API Documentation

## Endpoints

- User endpoints
  - GET /users - List all users
  - POST /users - Create new user
    - Requires authentication token
    - Validates input data
- Data endpoints
  - GET /data - Retrieve datasets
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Search for "authentication" - should find it in deeply nested list
        pattern = create_word_boundary_pattern("authentication")
        all_results = []
        for root in root_nodes:
            results = markdown_handler.search_in_node_subtree(root, pattern, include_descendants=True)
            all_results.extend(results)
        
        assert len(all_results) >= 1
        
        # Should find the nested list item
        nested_results = [r for r in all_results if "authentication token" in markdown_handler.get_node_content(r)]
        assert len(nested_results) >= 1

    def test_mixed_content_types_all_searchable(self, markdown_handler, temp_markdown_file):
        """Test that all content types within a section are searchable."""
        content = """# Complete Guide

This guide covers everything you need.

## Installation

To install the package:

```bash
pip install mypackage
```

Key points:
- Easy installation process
- No additional dependencies
- Cross-platform compatibility

### Configuration

Configure the application using environment variables:

```python
import os
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
```

Important configuration options:
1. Database connection string
2. Secret key for encryption
3. API endpoint URLs

## Usage Examples

Basic usage example:

```python
from mypackage import Client
client = Client(api_key='your-key')
result = client.fetch_data()
```

The client supports various authentication methods.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Test various searches across different content types
        test_searches = [
            ("installation", "Should find in heading and list item"),
            ("pip", "Should find in code block content"),
            ("environment", "Should find in paragraph under Configuration"),
            ("DATABASE_URL", "Should find in code block"),
            ("encryption", "Should find in numbered list"),
            ("authentication", "Should find in final paragraph"),
            ("Client", "Should find in code example"),
        ]
        
        for search_term, description in test_searches:
            pattern = create_word_boundary_pattern(search_term)
            all_results = []
            for root in root_nodes:
                results = markdown_handler.search_in_node_subtree(root, pattern, include_descendants=True)
                all_results.extend(results)
            
            assert len(all_results) >= 1, f"Failed to find '{search_term}': {description}"

    def test_code_blocks_not_parsed_as_separate_nodes(self, markdown_handler, temp_markdown_file):
        """Test that code blocks are included in section content, not separate nodes."""
        content = """# Code Examples

Here are some examples:

```python
def hello():
    print("Hello, World!")
    return "success"
```

The function above demonstrates basic syntax.

```bash
echo "Command line example"
ls -la
```

These commands show file listing.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Should have only heading nodes, not separate code block nodes
        heading_nodes = [node for node in root_nodes if node.node_type == 'heading']
        assert len(heading_nodes) == 1
        
        # The heading content should include code block text
        main_heading = heading_nodes[0]
        heading_content = markdown_handler.get_node_content(main_heading)
        
        # Should include code content as part of section
        assert "def hello" in heading_content
        assert "print" in heading_content
        assert "echo" in heading_content
        assert "ls -la" in heading_content

    def test_hierarchical_search_respects_markdown_structure(self, markdown_handler, temp_markdown_file):
        """Test that hierarchical search works correctly with markdown structure."""
        content = """# Programming Languages

## Python

Python is a high-level programming language.

### Functions in Python

Functions are defined with def keyword.

```python
def example_function():
    return "Hello"
```

### Classes in Python

Classes use the class keyword.

## JavaScript

JavaScript is a dynamic programming language.

### Functions in JavaScript  

Functions can be defined multiple ways.

```javascript
function example() {
    return "Hello";
}
```
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # First, find all "Python" sections
        python_pattern = create_word_boundary_pattern("Python")
        python_results = []
        for root in root_nodes:
            results = markdown_handler.search_in_node_subtree(root, python_pattern, include_descendants=False)  # Early termination
            python_results.extend(results)
        
        assert len(python_results) >= 1
        
        # Now search for "Functions" within Python sections
        function_results = []
        for python_node in python_results:
            function_pattern = create_word_boundary_pattern("Functions")
            results = markdown_handler.search_in_node_subtree(python_node, function_pattern, include_descendants=True)
            function_results.extend(results)
        
        assert len(function_results) >= 1
        
        # Verify we found results in the Python section specifically
        # With proper hierarchy, Python and JavaScript should be separate sections
        python_function_sections = []
        for result in function_results:
            content = markdown_handler.get_node_content(result)
            # Look for results that are clearly in Python section
            if "def example_function" in content and "JavaScript" not in content:
                python_function_sections.append(result)
            elif "Functions in Python" in content:
                python_function_sections.append(result)
        
        assert len(python_function_sections) >= 1, "Should find Python function content specifically"

    def test_empty_sections_handled_correctly(self, markdown_handler, temp_markdown_file):
        """Test that empty sections don't break content extraction."""
        content = """# Empty Section Test

## Section with Content

This section has content.

## Empty Section

## Another Section with Content

This has content too.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        
        # Should handle all sections without errors
        # With proper hierarchy, H2 sections should be children of H1
        assert len(root_nodes) == 1  # Should have one H1 root
        main_section = root_nodes[0]
        subsections = main_section.children
        assert len(subsections) >= 3  # Should have H2 subsections
        
        # Test all subsections
        for node in [main_section] + subsections:
            content = markdown_handler.get_node_content(node)
            assert isinstance(content, str)
            
            # Find the empty section specifically
            if node.text == "Empty Section":
                # Should have only heading text, no body content
                assert content.strip() == "Empty Section"

    def test_special_markdown_characters_searchable(self, markdown_handler, temp_markdown_file):
        """Test that content with special markdown characters is searchable."""
        content = """# Special Characters Test

This text has *emphasis* and **strong** formatting.

`Inline code` snippets are included.

> This is a blockquote with important information.

Links like [example](http://example.com) should be searchable.

Tables should work:
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

And horizontal rules:

---

More content after the rule.
"""
        
        with open(temp_markdown_file, 'w') as f:
            f.write(content)
        
        root_nodes = markdown_handler.get_root_nodes(temp_markdown_file)
        main_section = root_nodes[0]
        
        # Test various special character content
        test_terms = [
            "emphasis",      # From *emphasis*
            "strong",        # From **strong**
            "Inline",        # From `inline code`
            "blockquote",    # From blockquote
            "example.com",   # From link
            "Column",        # From table
            "Data",          # From table data
            "horizontal",    # From text after rule
        ]
        
        for term in test_terms:
            pattern = create_word_boundary_pattern(term)
            results = markdown_handler.search_in_node_subtree(main_section, pattern, include_descendants=True)
            assert len(results) >= 1, f"Could not find '{term}' in markdown content with special characters"