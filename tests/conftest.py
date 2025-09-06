#!/usr/bin/env python3
"""
Pytest configuration and fixtures for Knowledgebase Indexer tests.

Provides common fixtures and test utilities for both unit and integration tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigLoader
from logging_config import AppLogger
from core_handlers import handler_registry
from handlers.freeplane_handler import FreeplaneHandler
from handlers.markdown_handler import MarkdownHandler


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Set up logging for all tests."""
    log_file = AppLogger.setup_logging(
        console_level="WARNING",  # Keep console quiet during tests
        enable_file_logging=True
    )
    yield log_file
    # Cleanup handled by tmpdir fixtures


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp(prefix="kbi_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "directories": {
            "include": ["**/*.mm", "**/*.md"],
            "exclude": ["**/test_*.md"]
        },
        "keywords": {
            "files": ["keywords.txt"]
        },
        "output": {
            "file": "test_index.mm",
            "format": "freeplane"
        },
        "file_types": {
            "freeplane": {
                "extensions": [".mm"],
                "handler": "FreeplaneHandler",
                "hierarchy_config": {
                    "type": "xml_nodes",
                    "parent_element": "node",
                    "child_selector": "./node"
                }
            },
            "markdown": {
                "extensions": [".md", ".markdown"],
                "handler": "MarkdownHandler",
                "hierarchy_config": {
                    "type": "composite",
                    "structures": [
                        {"type": "heading_levels"},
                        {"type": "nested_lists"}
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_freeplane_content():
    """Sample Freeplane mind map XML content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<map version="freeplane 1.12.1">
    <node ID="ID_123456" CREATED="20240101T120000" MODIFIED="20240101T120000" TEXT="Root Node">
        <node ID="ID_234567" CREATED="20240101T120001" MODIFIED="20240101T120001" TEXT="Child 1">
            <node ID="ID_345678" CREATED="20240101T120002" MODIFIED="20240101T120002" TEXT="Grandchild 1"/>
        </node>
        <node ID="ID_456789" CREATED="20240101T120003" MODIFIED="20240101T120003" TEXT="Child 2"/>
    </node>
</map>'''


@pytest.fixture
def sample_markdown_content():
    """Sample Markdown content with hierarchy."""
    return '''# Main Topic

This is some introductory content for the main topic.

## Subtopic A

Content for subtopic A.

### Detail 1

Detailed information about subtopic A.

- List item 1
  - Nested item 1
  - Nested item 2
- List item 2

## Subtopic B

Content for subtopic B.

### Detail 2

More detailed information.

```python
def example_function():
    return "Hello World"
```
'''


@pytest.fixture
def sample_keyword_content():
    """Sample keyword file content."""
    return '''# Sample keywords
Programming Concepts
\tFunctions
\t\tfunction:definition
\t\tasync:function
\tClasses
\t\tclass:inheritance
\t\tinterface:implementation

Documentation
\tAPI Documentation
\t\tapi:reference
\tUser Guides
\t\ttutorial:beginner
'''


@pytest.fixture
def test_files(temp_dir, sample_freeplane_content, sample_markdown_content, sample_keyword_content):
    """Create test files in temporary directory."""
    files = {}
    
    # Create test files
    mm_file = temp_dir / "test.mm"
    mm_file.write_text(sample_freeplane_content)
    files['freeplane'] = str(mm_file)
    
    md_file = temp_dir / "test.md"
    md_file.write_text(sample_markdown_content)
    files['markdown'] = str(md_file)
    
    kw_file = temp_dir / "keywords.txt"
    kw_file.write_text(sample_keyword_content)
    files['keywords'] = str(kw_file)
    
    # Create subdirectory structure
    sub_dir = temp_dir / "subdir"
    sub_dir.mkdir()
    
    sub_md = sub_dir / "sub.md"
    sub_md.write_text("# Sub Document\n\nContent in subdirectory.")
    files['sub_markdown'] = str(sub_md)
    
    return files


@pytest.fixture
def config_loader():
    """Provide ConfigLoader instance."""
    return ConfigLoader()


@pytest.fixture
def initialized_handlers():
    """Provide initialized handler registry."""
    # Clear existing handlers
    handler_registry._handlers.clear()
    handler_registry._instances.clear()
    
    # Register test handlers
    handler_registry.register_handler('FreeplaneHandler', FreeplaneHandler)
    handler_registry.register_handler('MarkdownHandler', MarkdownHandler)
    
    yield handler_registry
    
    # Cleanup
    handler_registry._handlers.clear()
    handler_registry._instances.clear()


class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def create_complex_freeplane(file_path: Path, depth: int = 3, nodes_per_level: int = 3):
        """Create a complex Freeplane file for testing."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="freeplane 1.12.1">
    <node ID="ROOT" CREATED="20240101T120000" MODIFIED="20240101T120000" TEXT="Complex Root">
'''
        
        def add_nodes(level: int, parent_id: str, max_depth: int):
            if level >= max_depth:
                return ""
            
            nodes_content = ""
            for i in range(nodes_per_level):
                node_id = f"NODE_{level}_{i}"
                text = f"Level {level} Node {i}"
                
                # Add some nodes with rich content
                rich_content = ""
                if i == 0:
                    rich_content = '''
        <richcontent TYPE="NOTE">
            <html>
                <body>
                    <p>This is a note with <b>rich content</b></p>
                </body>
            </html>
        </richcontent>'''
                
                nodes_content += f'''
        <node ID="{node_id}" CREATED="20240101T12000{level}" MODIFIED="20240101T12000{level}" TEXT="{text}">{rich_content}
            {add_nodes(level + 1, node_id, max_depth)}
        </node>'''
            
            return nodes_content
        
        content += add_nodes(1, "ROOT", depth)
        content += '''
    </node>
</map>'''
        
        file_path.write_text(content)
        return str(file_path)
    
    @staticmethod
    def create_complex_markdown(file_path: Path):
        """Create a complex Markdown file for testing."""
        content = '''# Complex Document

This is a complex markdown document for testing hierarchical parsing.

## Section 1: Getting Started

Welcome to this comprehensive guide.

### 1.1 Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
  - With pip installed
  - Virtual environment support
- Git version control
- A text editor

### 1.2 Installation Steps

1. Clone the repository
2. Create virtual environment
3. Install dependencies

## Section 2: Configuration

Configuration involves several steps:

### 2.1 Basic Configuration

Set up the basic configuration file:

```yaml
# config.yml
debug: true
logging:
  level: INFO
```

### 2.2 Advanced Configuration

For advanced users:

- Custom handlers
  - File type handlers
  - Output formatters
- Performance tuning
  - Cache settings
  - Memory limits

## Section 3: Usage Examples

Here are some practical examples:

### 3.1 Basic Usage

Simple command line usage:

```bash
python mmdir.py --config config.yml
```

### 3.2 Advanced Usage

With keyword searching:

```bash
python mmdir.py --debug --keywords advanced.txt
```

## Conclusion

This document covers the essential aspects of using the system.

#tags #documentation #tutorial
'''
        
        file_path.write_text(content)
        return str(file_path)


@pytest.fixture
def test_data_generator():
    """Provide TestDataGenerator instance."""
    return TestDataGenerator()


# Markers for different test types
pytest.mark.quick = pytest.mark.quick or pytest.mark.unit
pytest.mark.slow = pytest.mark.slow or pytest.mark.integration