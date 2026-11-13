#!/usr/bin/env python3
"""Configuration management with schema validation."""

import copy
import json
import yaml
import jsonschema
from pathlib import Path
from typing import Dict, Any, List, Optional


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

        config = self._load_with_extends(Path(discovered_path), [])

        config = self._normalize_enums(config)
        self.validate_config(config)
        return self._merge_with_defaults(config)

    @staticmethod
    def _read_config_file(path: Path) -> Dict[str, Any]:
        """Parse one config file (YAML or JSON) into a mapping."""
        with open(path, 'r') as f:
            if path.suffix in ('.yml', '.yaml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Configuration error: {path} must contain a mapping at the top level"
            )
        return data

    def _load_with_extends(self, path: Path, chain: List[Path]) -> Dict[str, Any]:
        """Load a config file, resolving its `extends:` chain (R-CFG-016..020).

        `extends` names a base config, resolved relative to the extending
        file's directory (`~` expanded).  The base is loaded first (itself
        possibly extending another), then this file is deep-merged over it.
        `chain` holds the files already on the resolution path, for cycle
        detection (R-CFG-020).
        """
        resolved = path.expanduser().resolve()
        if resolved in chain:
            cycle = ' -> '.join(str(p) for p in chain + [resolved])
            raise ValueError(f"Configuration error: circular extends: {cycle}")
        config = self._read_config_file(resolved)

        base_ref = config.pop('extends', None)
        if base_ref is None:
            return config
        if not isinstance(base_ref, str) or not base_ref.strip():
            raise ValueError(
                f"Configuration error: 'extends' in {resolved} must be a file path"
            )
        base_path = Path(base_ref).expanduser()
        if not base_path.is_absolute():
            base_path = resolved.parent / base_path
        if not base_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {base_path} (extended by {resolved})"
            )
        base = self._load_with_extends(base_path, chain + [resolved])
        return self._deep_merge(base, config)

    @classmethod
    def _deep_merge(cls, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge `override` onto `base` (R-CFG-018).

        Mappings merge key by key, recursively, with `override` winning.
        Lists and scalars in `override` replace the base value wholesale, so
        an extending config can clear an inherited list with `[]`.
        """
        merged = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = cls._deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

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

        # `update_cards` tunes the --update-cards pass (e.g. ignore_unmanaged).
        if "update_cards" in config:
            merged["update_cards"] = config["update_cards"]

        return merged