#!/usr/bin/env python3
"""Configuration management with schema validation."""

import json
import yaml
import jsonschema
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Handles configuration loading and validation."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """Initialize with optional custom schema path."""
        self.schema_path = schema_path or self._get_default_schema_path()
        self._schema = None
    
    def _get_default_schema_path(self) -> str:
        """Get the default schema file path."""
        return str(Path(__file__).parent / "config_schema.json")
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load and cache the JSON schema."""
        if self._schema is None:
            with open(self.schema_path, 'r') as f:
                self._schema = json.load(f)
        return self._schema
    
    def discover_config(self, config_path: Optional[str] = None) -> Optional[str]:
        """Discover configuration file in priority order."""
        if config_path:
            if Path(config_path).exists():
                return config_path
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Priority order for config discovery
        candidates = [
            Path.cwd() / "config" / "kbi.yml",
            Path.cwd() / "config" / "kbi.yaml",
            Path.cwd() / "kbi.yml",
            Path.cwd() / "kbi.yaml",
            Path.home() / ".config" / "kbi" / "config.yml",
            Path.home() / ".config" / "kbi" / "config.yaml",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        
        return None
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load and validate configuration."""
        discovered_path = self.discover_config(config_path)
        
        if not discovered_path:
            # Return default configuration
            return self._get_default_config()
        
        with open(discovered_path, 'r') as f:
            if discovered_path.endswith(('.yml', '.yaml')):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        
        self.validate_config(config)
        return self._merge_with_defaults(config)
    
    def validate_config(self, config: Dict[str, Any]):
        """Validate configuration against schema."""
        schema = self._load_schema()
        try:
            jsonschema.validate(config, schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Configuration validation error: {e.message}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "directories": {
                "include": ["src/", "docs/", "."],
                "exclude": ["**/node_modules/**", "**/.git/**", "**/build/**", "**/__pycache__/**", "**/.venv/**"]
            },
            "keywords": {
                "files": []
            },
            "output": {
                "file": "index.mm",
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
                    },
                    "search_config": {
                        "content_fields": ["TEXT", "RICHCONTENT"]
                    },
                    "link_config": {
                        "format": "{path}#{fragment}",
                        "supports_fragments": True
                    }
                },
                "markdown": {
                    "extensions": [".md", ".markdown"],
                    "handler": "MarkdownHandler",
                    "hierarchy_config": {
                        "type": "composite",
                        "structures": [
                            {
                                "type": "heading_levels",
                                "heading_tags": ["h1", "h2", "h3", "h4", "h5", "h6"],
                                "content_scope": "heading_plus_content_until_next_heading"
                            },
                            {
                                "type": "nested_lists",
                                "list_types": ["ul", "ol"],
                                "nesting_logic": "indentation_based"
                            }
                        ]
                    },
                    "search_config": {
                        "content_fields": ["heading_text", "section_content", "list_item_text"]
                    },
                    "link_config": {
                        "format": "{path}#{anchor}",
                        "supports_fragments": True
                    }
                }
            }
        }
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with defaults."""
        default_config = self._get_default_config()
        
        # Simple deep merge - in production would use more sophisticated merging
        merged = default_config.copy()
        
        if "directories" in config:
            merged["directories"].update(config["directories"])
        
        if "keywords" in config:
            merged["keywords"].update(config["keywords"])
        
        if "output" in config:
            merged["output"].update(config["output"])
        
        if "file_types" in config:
            merged["file_types"].update(config["file_types"])
        
        return merged