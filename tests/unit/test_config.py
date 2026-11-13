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
        # directories.include is the only required field
        invalid_config = {
            "directories": {}  # include is required within directories
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
        assert 'file_types' not in config   # handlers are built in, not declared in config

        assert isinstance(config['directories']['include'], list)
        assert isinstance(config['directories']['exclude'], list)
    
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
        
        # `types` is carried through when given; absent here → not added
        assert 'types' not in merged
        merged2 = loader._merge_with_defaults({**user_config, "types": {"include": ["card"]}})
        assert merged2['types'] == {"include": ["card"]}
    
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
    
    def test_load_no_config_raises(self, tmp_path, monkeypatch):
        """A config is required: no path and nothing discoverable -> error."""
        monkeypatch.chdir(tmp_path)            # isolated cwd with no kbi.yml
        monkeypatch.setattr(Path, "home", lambda: tmp_path)  # no ~/.config/kbi
        loader = ConfigLoader()
        with pytest.raises(ValueError, match="No configuration file"):
            loader.load_config()  # No config file provided or discovered


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
    
    def test_schema_rejects_invalid_type(self):
        """Schema rejects an unknown built-in type name in `types`."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)

        invalid_config = {
            "directories": {"include": ["*.md"]},
            "output": {"file": "test.mm"},
            "types": {"include": ["bogus"]},   # not a built-in type
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_config, schema)

    def test_schema_accepts_types_include_exclude(self):
        """Schema accepts include/exclude of valid built-in type names."""
        schema_path = Path(__file__).parent.parent.parent / "config_schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        for types in ({"include": ["card"]}, {"exclude": ["card", "freeplane"]}):
            jsonschema.validate(
                {"directories": {"include": ["*.md"]}, "output": {"file": "o.mm"}, "types": types},
                schema)

@pytest.mark.quick
class TestConfigExtends:
    """`extends:` config inheritance (R-CFG-016..020)."""

    BASE = {
        "directories": {"include": ["/a", "/b"], "exclude": ["**/.git/**"]},
        "keywords": {"files": ["/kw.txt"]},
        "output": {"format": "freeplane"},
        "types": {"include": ["card"]},
        "update_cards": {"ignore_unmanaged": ["~/dev/linux"]},
    }

    @staticmethod
    def _write(path: Path, data) -> Path:
        path.write_text(yaml.safe_dump(data))
        return path

    def test_inherits_and_overrides(self, tmp_path):
        """Child inherits unspecified keys; mappings merge, child wins (R-CFG-016, -018)."""
        self._write(tmp_path / "base.yml", self.BASE)
        child = self._write(tmp_path / "child.yml", {
            "extends": "base.yml",
            "output": {"file": "/out", "format": "markdown"},
        })
        cfg = ConfigLoader().load_config(str(child))
        assert cfg["directories"] == self.BASE["directories"]
        assert cfg["types"] == {"include": ["card"]}
        assert cfg["update_cards"] == {"ignore_unmanaged": ["~/dev/linux"]}
        assert cfg["output"] == {"file": "/out", "format": "markdown"}
        assert "extends" not in cfg

    def test_lists_replace_not_append(self, tmp_path):
        """A child list replaces the inherited one; `[]` clears it (R-CFG-018)."""
        self._write(tmp_path / "base.yml", self.BASE)
        child = self._write(tmp_path / "child.yml", {
            "extends": "base.yml",
            "keywords": {"files": []},
            "directories": {"include": ["/c"]},
        })
        cfg = ConfigLoader().load_config(str(child))
        assert cfg["keywords"]["files"] == []
        assert cfg["directories"]["include"] == ["/c"]
        assert cfg["directories"]["exclude"] == ["**/.git/**"]   # sibling key kept

    def test_path_relative_to_extending_file(self, tmp_path, monkeypatch):
        """`extends` resolves against the extending file's directory, not cwd (R-CFG-017)."""
        (tmp_path / "shared").mkdir()
        (tmp_path / "configs").mkdir()
        self._write(tmp_path / "shared" / "base.yml", self.BASE)
        child = self._write(tmp_path / "configs" / "child.yml",
                            {"extends": "../shared/base.yml"})
        monkeypatch.chdir(tmp_path)   # cwd-relative lookup would miss
        cfg = ConfigLoader().load_config(str(child))
        assert cfg["directories"]["include"] == ["/a", "/b"]

    def test_chained_extends(self, tmp_path):
        """A base may itself extend another config (R-CFG-019)."""
        self._write(tmp_path / "root.yml", self.BASE)
        self._write(tmp_path / "mid.yml", {"extends": "root.yml",
                                           "types": {"include": ["card", "markdown"]}})
        leaf = self._write(tmp_path / "leaf.yml", {"extends": "mid.yml",
                                                    "output": {"format": "markdown"}})
        cfg = ConfigLoader().load_config(str(leaf))
        assert cfg["types"] == {"include": ["card", "markdown"]}
        assert cfg["output"]["format"] == "markdown"
        assert cfg["update_cards"] == {"ignore_unmanaged": ["~/dev/linux"]}

    def test_cycle_rejected(self, tmp_path):
        """Circular extends raises a clear error (R-CFG-020)."""
        self._write(tmp_path / "a.yml", {"extends": "b.yml", **self.BASE})
        self._write(tmp_path / "b.yml", {"extends": "a.yml"})
        with pytest.raises(ValueError, match="circular extends"):
            ConfigLoader().load_config(str(tmp_path / "a.yml"))

    def test_missing_base_rejected(self, tmp_path):
        """A missing base names both files in the error (R-CFG-020)."""
        child = self._write(tmp_path / "child.yml", {"extends": "nope.yml"})
        with pytest.raises(FileNotFoundError, match="extended by"):
            ConfigLoader().load_config(str(child))

    def test_merged_result_is_validated(self, tmp_path):
        """Validation runs on the merged config, so a child may omit required keys
        it inherits, but an invalid override is still rejected (R-CFG-016)."""
        self._write(tmp_path / "base.yml", self.BASE)
        bad = self._write(tmp_path / "bad.yml", {"extends": "base.yml",
                                                  "types": {"include": ["bogus"]}})
        with pytest.raises(ValueError, match="validation error"):
            ConfigLoader().load_config(str(bad))

    def test_base_not_mutated_between_loads(self, tmp_path):
        """Deep merge copies, so loading a child leaves the base's own load unchanged."""
        base = self._write(tmp_path / "base.yml", self.BASE)
        child = self._write(tmp_path / "child.yml", {"extends": "base.yml",
                                                      "output": {"format": "markdown"}})
        loader = ConfigLoader()
        loader.load_config(str(child))
        assert loader.load_config(str(base))["output"]["format"] == "freeplane"

    def test_repo_study25_md_inherits_ignore_list(self):
        """The shipped markdown catalog config shares its base's ignore list."""
        configs = Path(__file__).parent.parent.parent / "configs"
        md = ConfigLoader().load_config(str(configs / "Study25-cards-md.yml"))
        fp = ConfigLoader().load_config(str(configs / "Study25-cards.yml"))
        assert md["update_cards"] == fp["update_cards"]
        assert md["directories"] == fp["directories"]
        assert md["output"]["format"] == "markdown"
        assert md["keywords"]["files"] == []
