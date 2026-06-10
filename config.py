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
            Path.cwd() / "configs" / "kbi.yml",
            Path.cwd() / "configs" / "kbi.yaml",
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
            raise ValueError(
                "No configuration file provided or discovered. Pass a config "
                "path (run `kbi.py --sample-config` to scaffold one)."
            )

        with open(discovered_path, 'r') as f:
            if discovered_path.endswith(('.yml', '.yaml')):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        config = self._normalize_enums(config)
        self.validate_config(config)
        return self._merge_with_defaults(config)

    def _normalize_enums(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """YAML parses `on`/`off`/`yes`/`no` as booleans; coerce them back to the
        string enums the schema expects (output.partition_by_domain, output.views.*)
        so users can write `off`/`on` unquoted."""
        def s(v):
            return 'on' if v is True else 'off' if v is False else v
        out = config.get('output') if isinstance(config, dict) else None
        if isinstance(out, dict):
            if 'partition_by_domain' in out:
                out['partition_by_domain'] = s(out['partition_by_domain'])
            views = out.get('views')
            if isinstance(views, dict):
                for k in list(views):
                    views[k] = s(views[k])
        return config
    
    def validate_config(self, config: Dict[str, Any]):
        """Validate configuration against schema."""
        schema = self._load_schema()
        try:
            jsonschema.validate(config, schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Configuration validation error: {e.message}")
        types = config.get("types") or {}
        if "include" in types and "exclude" in types:
            raise ValueError(
                "Configuration validation error: 'types' must use either "
                "'include' or 'exclude', not both"
            )
    
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

        # `types` selects which built-in handlers to index (include/exclude by
        # name). Carry it through as-is; absence means all built-in types.
        if "types" in config:
            merged["types"] = config["types"]

        return merged