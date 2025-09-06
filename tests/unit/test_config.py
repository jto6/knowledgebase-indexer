#!/usr/bin/env python3
"""
Unit tests for configuration loading and validation.

Tests the ConfigLoader class and schema validation functionality.
"""

import pytest
import json
import yaml
from pathlib import Path
import tempfile
import jsonschema

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import ConfigLoader


@pytest.mark.quick
class TestConfigLoader:
    """Test cases for ConfigLoader class."""
    
    def test_default_schema_path(self):
        """Test that default schema path is correctly determined."""
        loader = ConfigLoader()
        schema_path = loader._get_default_schema_path()
        assert schema_path.endswith('config_schema.json')
        assert Path(schema_path).exists()
    
    def test_schema_loading(self):
        """Test JSON schema loading."""
        loader = ConfigLoader()
        schema = loader._load_schema()
        
        assert isinstance(schema, dict)
        assert 'type' in schema
        assert 'properties' in schema
        assert 'directories' in schema['properties']
        assert 'output' in schema['properties']
    
    def test_schema_caching(self):
        """Test that schema is cached after first load."""
        loader = ConfigLoader()
        schema1 = loader._load_schema()
        schema2 = loader._load_schema()
        
        assert schema1 is schema2  # Should be the same object reference
    
    def test_config_validation_valid(self, sample_config):
        """Test validation with valid configuration."""
        loader = ConfigLoader()
        # Should not raise any exception
        loader.validate_config(sample_config)
    
    def test_config_validation_missing_required(self):
        """Test validation fails with missing required fields."""
        loader = ConfigLoader()
        invalid_config = {
            "directories": {
                "include": ["**/*.md"]
            }
            # Missing required 'output' section
        }
        
        with pytest.raises(ValueError, match="Configuration validation error"):
            loader.validate_config(invalid_config)
    
    def test_config_validation_invalid_type(self):
        """Test validation fails with invalid field types."""
        loader = ConfigLoader()
        invalid_config = {
            "directories": {
                "include": "not_an_array"  # Should be array
            },
            "output": {
                "file": "test.mm"
            }
        }
        
        with pytest.raises(ValueError, match="Configuration validation error"):
            loader.validate_config(invalid_config)
    
    def test_default_config_structure(self):
        """Test that default configuration has expected structure."""
        loader = ConfigLoader()
        config = loader._get_default_config()
        
        assert 'directories' in config
        assert 'keywords' in config
        assert 'output' in config
        assert 'file_types' in config
        
        assert isinstance(config['directories']['include'], list)
        assert isinstance(config['directories']['exclude'], list)
        assert 'freeplane' in config['file_types']
        assert 'markdown' in config['file_types']
    
    def test_merge_with_defaults(self):
        """Test merging user config with defaults."""
        loader = ConfigLoader()
        user_config = {
            "directories": {
                "include": ["custom/*.md"],
                "exclude": ["temp/*"]
            },
            "output": {
                "file": "custom_output.mm"
            }
        }
        
        merged = loader._merge_with_defaults(user_config)
        
        # Should have user values
        assert merged['directories']['include'] == ["custom/*.md"]
        assert merged['directories']['exclude'] == ["temp/*"]
        assert merged['output']['file'] == "custom_output.mm"
        
        # Should have default values for unspecified fields
        assert 'file_types' in merged
        assert 'freeplane' in merged['file_types']
    
    def test_config_discovery_nonexistent(self, temp_dir, monkeypatch):
        """Test config discovery when no files exist."""
        # Change to temp directory where no config files exist
        monkeypatch.chdir(temp_dir)
        
        loader = ConfigLoader()
        result = loader.discover_config()
        
        # Should return None when no config files found
        assert result is None
    
    def test_config_discovery_explicit_path(self, temp_dir):
        """Test config discovery with explicit path."""
        loader = ConfigLoader()
        config_file = temp_dir / "test_config.yml"
        config_file.write_text("directories:\n  include: ['*.md']")
        
        result = loader.discover_config(str(config_file))
        assert result == str(config_file)
    
    def test_config_discovery_explicit_path_missing(self):
        """Test config discovery with non-existent explicit path."""
        loader = ConfigLoader()
        
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            loader.discover_config("/nonexistent/config.yml")
    
    def test_load_yaml_config(self, temp_dir, sample_config):
        """Test loading YAML configuration file."""
        loader = ConfigLoader()
        config_file = temp_dir / "test_config.yml"
        
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        
        loaded_config = loader.load_config(str(config_file))
        
        assert loaded_config['directories']['include'] == sample_config['directories']['include']
        assert loaded_config['output']['file'] == sample_config['output']['file']
    
    def test_load_json_config(self, temp_dir, sample_config):
        """Test loading JSON configuration file."""
        loader = ConfigLoader()
        config_file = temp_dir / "test_config.json"
        
        with open(config_file, 'w') as f:
            json.dump(sample_config, f)
        
        loaded_config = loader.load_config(str(config_file))
        
        assert loaded_config['directories']['include'] == sample_config['directories']['include']
        assert loaded_config['output']['file'] == sample_config['output']['file']
    
    def test_load_invalid_yaml(self, temp_dir):
        """Test loading invalid YAML file."""
        loader = ConfigLoader()
        config_file = temp_dir / "invalid.yml"
        config_file.write_text("invalid: yaml: content: [unclosed")
        
        with pytest.raises(Exception):  # Should raise YAML parsing error
            loader.load_config(str(config_file))
    
    def test_load_no_config_returns_defaults(self):
        """Test that loading without config file returns defaults."""
        loader = ConfigLoader()
        config = loader.load_config()  # No config file
        
        # Should get default config
        assert 'directories' in config
        assert 'output' in config
        assert config['output']['file'] == 'index.mm'


@pytest.mark.quick
class TestConfigSchema:
    """Test cases for configuration schema validation."""
    
    def test_schema_file_exists(self):
        """Test that schema file exists and is valid JSON."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        assert schema_path.exists()
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        assert isinstance(schema, dict)
        assert 'type' in schema
    
    def test_schema_validates_minimal_config(self):
        """Test schema validates minimal valid configuration."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        
        minimal_config = {
            "directories": {
                "include": ["*.md"]
            },
            "output": {
                "file": "test.mm"
            }
        }
        
        # Should not raise
        jsonschema.validate(minimal_config, schema)
    
    def test_schema_rejects_invalid_extensions(self):
        """Test schema rejects invalid file extensions."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        
        invalid_config = {
            "directories": {"include": ["*.md"]},
            "output": {"file": "test.mm"},
            "file_types": {
                "test": {
                    "extensions": ["invalid"],  # Missing dot
                    "handler": "TestHandler"
                }
            }
        }
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_config, schema)
    
    def test_schema_validates_hierarchy_configs(self):
        """Test schema validates different hierarchy configurations."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        
        # XML nodes config
        xml_config = {
            "directories": {"include": ["*.mm"]},
            "output": {"file": "test.mm"},
            "file_types": {
                "test": {
                    "extensions": [".mm"],
                    "handler": "TestHandler",
                    "hierarchy_config": {
                        "type": "xml_nodes",
                        "parent_element": "node",
                        "child_selector": "./node"
                    }
                }
            }
        }
        
        jsonschema.validate(xml_config, schema)
        
        # Composite config
        composite_config = {
            "directories": {"include": ["*.md"]},
            "output": {"file": "test.mm"},
            "file_types": {
                "test": {
                    "extensions": [".md"],
                    "handler": "TestHandler",
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
        
        jsonschema.validate(composite_config, schema)