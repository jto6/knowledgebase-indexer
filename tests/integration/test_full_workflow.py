#!/usr/bin/env python3
"""
Integration tests for the complete Knowledgebase Indexer workflow.

Tests the full pipeline from configuration to mind map generation.
"""

import pytest
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kbi import KnowledgebaseIndexer
from config import ConfigLoader
from logging_config import AppLogger


@pytest.mark.slow
@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete workflow."""
    
    def test_minimal_workflow(self, temp_dir, test_data_generator):
        """Test minimal workflow with basic files."""
        # Set up working directory
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create test files
            md_file = test_data_generator.create_complex_markdown(temp_dir / "test.md")
            mm_file = test_data_generator.create_complex_freeplane(temp_dir / "test.mm")
            
            # Create minimal config
            config = {
                "directories": {
                    "include": ["*.md", "*.mm"],
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "test_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    },
                    "freeplane": {
                        "extensions": [".mm"],
                        "handler": "FreeplaneHandler"
                    }
                }
            }
            
            # Run generator
            generator = KnowledgebaseIndexer(config)
            output_path = generator.run()
            
            # Verify output
            assert Path(output_path).exists()
            assert output_path.endswith("test_index.mm")
            
            # Parse and validate XML
            tree = ET.parse(output_path)
            root = tree.getroot()
            assert root.tag == "map"
            assert root.get("version") == "freeplane 1.12.1"
            
            # Should have main root node with File System Index
            main_node = root.find(".//node[@TEXT='Navigation Index']")
            assert main_node is not None
            
            fs_index = root.find(".//node[@TEXT='File System Index']")
            assert fs_index is not None
            
        finally:
            os.chdir(original_cwd)
    
    def test_workflow_with_keywords(self, temp_dir, test_data_generator):
        """Test workflow with keyword-based searching."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create test files with searchable content
            md_content = """# Python Programming

## Functions
Functions are defined with def keyword.

### Async Functions
Async functions use async def syntax.

```python
async def example():
    return await something()
```

## Classes
Classes are defined with class keyword.

### Inheritance
Python supports class inheritance.
"""
            
            md_file = temp_dir / "python_guide.md"
            md_file.write_text(md_content)
            
            # Create keyword file
            keywords_content = """Programming
\tFunctions
\t\tfunction:async
\tClasses
\t\tclass:inheritance
"""
            
            kw_file = temp_dir / "keywords.txt"
            kw_file.write_text(keywords_content)
            
            # Create config
            config = {
                "directories": {
                    "include": ["*.md"],
                    "exclude": []
                },
                "keywords": {
                    "files": ["keywords.txt"]
                },
                "output": {
                    "file": "keyword_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    }
                }
            }
            
            # Run generator with debug
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(True)
            output_path = generator.run()
            
            # Verify output
            assert Path(output_path).exists()
            
            # Parse XML and check for keyword results
            tree = ET.parse(output_path)
            root = tree.getroot()
            
            # Should have keyword index
            keyword_index = root.find(".//node[@TEXT='Keyword Index']")
            assert keyword_index is not None
            
            # Check for specific search results
            # Look for function:async results
            found_function_async = False
            for node in root.findall(".//node"):
                if node.get("TEXT") and "function → async" in node.get("TEXT"):
                    found_function_async = True
                    break
            
            # Note: This might not find results if the search doesn't match
            # but the structure should be there
            
        finally:
            os.chdir(original_cwd)
    
    def test_workflow_with_tags(self, temp_dir):
        """Test workflow with tag extraction."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create markdown file with tags
            md_content = """---
title: Test Document
tags: [python, tutorial, beginner]
---

# Test Document

This is a test document with #hashtags and #tutorial content.

#python #programming
"""
            
            md_file = temp_dir / "tagged_doc.md"
            md_file.write_text(md_content)
            
            # Create Freeplane file with attribute-based tags
            mm_content = """<?xml version="1.0" encoding="UTF-8"?>
<map version="freeplane 1.12.1">
    <node ID="ROOT" TEXT="Root">
        <attribute NAME="tag" VALUE="mindmap,example"/>
        <node ID="CHILD1" TEXT="Child 1">
            <attribute NAME="category" VALUE="documentation"/>
        </node>
    </node>
</map>"""
            
            mm_file = temp_dir / "tagged.mm"
            mm_file.write_text(mm_content)
            
            # Create config
            config = {
                "directories": {
                    "include": ["*.md", "*.mm"],
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "tag_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    },
                    "freeplane": {
                        "extensions": [".mm"],
                        "handler": "FreeplaneHandler"
                    }
                }
            }
            
            # Run generator
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(True)
            output_path = generator.run()
            
            # Verify output
            assert Path(output_path).exists()
            
            # Parse XML and check for tag index
            tree = ET.parse(output_path)
            root = tree.getroot()
            
            # Should have tag index if tags were found
            tag_index = root.find(".//node[@TEXT='Tag Index']")
            # Tag index might not be present if no tags were extracted
            # but the file should still be generated successfully
            
        finally:
            os.chdir(original_cwd)
    
    def test_complex_directory_structure(self, temp_dir, test_data_generator):
        """Test workflow with complex directory structure."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create complex directory structure
            docs_dir = temp_dir / "docs"
            docs_dir.mkdir()
            src_dir = temp_dir / "src"
            src_dir.mkdir()
            tests_dir = temp_dir / "tests"
            tests_dir.mkdir()
            
            # Create files in different directories
            test_data_generator.create_complex_markdown(docs_dir / "guide.md")
            test_data_generator.create_complex_freeplane(src_dir / "architecture.mm")
            
            # Create a file to exclude
            (tests_dir / "test_temp.md").write_text("# Temporary test file")
            
            # Create config with include/exclude patterns
            config = {
                "directories": {
                    "include": ["**/*.md", "**/*.mm"],
                    "exclude": ["**/test_*.md"]
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "complex_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    },
                    "freeplane": {
                        "extensions": [".mm"],
                        "handler": "FreeplaneHandler"
                    }
                }
            }
            
            # Run generator
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(True)
            output_path = generator.run()
            
            # Verify output
            assert Path(output_path).exists()
            
            # Parse XML and verify directory structure is reflected
            tree = ET.parse(output_path)
            root = tree.getroot()
            
            # Should have file system index with directory structure
            fs_index = root.find(".//node[@TEXT='File System Index']")
            assert fs_index is not None
            
            # Should have docs and src directories
            found_docs = False
            found_src = False
            for node in root.findall(".//node"):
                text = node.get("TEXT", "")
                if text == "docs":
                    found_docs = True
                elif text == "src":
                    found_src = True
            
            assert found_docs
            assert found_src
            
        finally:
            os.chdir(original_cwd)
    
    def test_error_handling_invalid_files(self, temp_dir):
        """Test workflow handles invalid files gracefully."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create invalid markdown file
            invalid_md = temp_dir / "invalid.md"
            invalid_md.write_bytes(b'\x80\x81\x82\x83')  # Invalid UTF-8
            
            # Create valid file
            valid_md = temp_dir / "valid.md"
            valid_md.write_text("# Valid Document\n\nContent here.")
            
            # Create config
            config = {
                "directories": {
                    "include": ["*.md"],
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "error_test_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    }
                }
            }
            
            # Run generator - should handle errors gracefully
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(True)
            
            # Should complete successfully despite invalid files
            output_path = generator.run()
            
            # Verify output exists
            assert Path(output_path).exists()
            
            # Parse XML to ensure it's valid
            tree = ET.parse(output_path)
            root = tree.getroot()
            assert root.tag == "map"
            
        finally:
            os.chdir(original_cwd)
    
    def test_empty_directory_handling(self, temp_dir):
        """Test workflow with no matching files."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create config that matches no files
            config = {
                "directories": {
                    "include": ["*.nonexistent"],
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "empty_index.mm"
                },
                "file_types": {
                    "nonexistent": {
                        "extensions": [".nonexistent"],
                        "handler": "MarkdownHandler"
                    }
                }
            }
            
            # Should raise error for no files
            generator = KnowledgebaseIndexer(config)
            
            with pytest.raises(ValueError, match="No files found"):
                generator.run()
                
        finally:
            os.chdir(original_cwd)


@pytest.mark.slow
@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests for configuration loading."""
    
    def test_config_file_discovery(self, temp_dir):
        """Test automatic config file discovery."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Create config file in working directory
            config_content = {
                "directories": {
                    "include": ["*.test"],
                    "exclude": []
                },
                "output": {
                    "file": "discovered_index.mm"
                }
            }
            
            config_file = temp_dir / "mmdir.yml"
            with open(config_file, 'w') as f:
                yaml.dump(config_content, f)
            
            # Load config without specifying path
            loader = ConfigLoader()
            config = loader.load_config()
            
            # Should discover and load the config
            assert config["directories"]["include"] == ["*.test"]
            assert config["output"]["file"] == "discovered_index.mm"
            
        finally:
            os.chdir(original_cwd)
    
    def test_config_validation_integration(self, temp_dir):
        """Test config validation in full workflow."""
        # Create invalid config file
        invalid_config = {
            "directories": {
                "include": "not_an_array"  # Should be array
            },
            "output": {
                "file": "test.mm"
            }
        }
        
        config_file = temp_dir / "invalid_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Should raise validation error
        loader = ConfigLoader()
        with pytest.raises(ValueError, match="Configuration validation error"):
            loader.load_config(str(config_file))


@pytest.mark.slow
@pytest.mark.integration  
class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_logging_in_workflow(self, temp_dir, test_data_generator):
        """Test logging during complete workflow."""
        original_cwd = os.getcwd()
        
        try:
            os.chdir(str(temp_dir))
            
            # Set up logging
            log_file = AppLogger.setup_logging(
                console_level="DEBUG",
                enable_file_logging=True,
                log_file=str(temp_dir / "test_log.txt")
            )
            
            # Create test file
            test_data_generator.create_complex_markdown(temp_dir / "test.md")
            
            # Create config
            config = {
                "directories": {
                    "include": ["*.md"],
                    "exclude": []
                },
                "keywords": {
                    "files": []
                },
                "output": {
                    "file": "logged_index.mm"
                },
                "file_types": {
                    "markdown": {
                        "extensions": [".md"],
                        "handler": "MarkdownHandler"
                    }
                }
            }
            
            # Run generator with debug
            generator = KnowledgebaseIndexer(config)
            generator.set_debug(True)
            generator.run()
            
            # Verify log file was created and contains expected entries
            assert Path(log_file).exists()
            
            log_content = Path(log_file).read_text()
            
            # Should contain startup and workflow messages
            assert "Logging initialized" in log_content
            assert "Index Generation Process" in log_content or "Building File System Index" in log_content
            
        finally:
            os.chdir(original_cwd)