#!/usr/bin/env python3
"""Base file handler interface and common functionality."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator, Union
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class HierarchicalNode:
    """Represents a node in a hierarchical structure."""
    id: str
    content: str
    text: str = ""
    file_path: Optional[str] = None
    parent: Optional['HierarchicalNode'] = None
    children: List['HierarchicalNode'] = None
    node_type: str = "generic"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}
        if not self.text:
            self.text = self.content
    
    def add_child(self, child: 'HierarchicalNode'):
        """Add a child node."""
        child.parent = self
        self.children.append(child)
    
    def get_descendants(self) -> List['HierarchicalNode']:
        """Get all descendant nodes."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def find_children_by_type(self, node_type: str) -> List['HierarchicalNode']:
        """Find direct children of specified type."""
        return [child for child in self.children if child.node_type == node_type]
    
    def get_path(self) -> List[str]:
        """Get path from root to this node."""
        path = []
        current = self
        while current:
            path.append(current.text or current.id)
            current = current.parent
        return list(reversed(path))


class FileHandler(ABC):
    """Abstract base class for file type handlers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize handler with configuration."""
        self.config = config
        self.hierarchy_config = config.get('hierarchy_config', {})
        self.search_config = config.get('search_config', {})
        self.link_config = config.get('link_config', {})
    
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Check if this handler can process the given file."""
        pass
    
    @abstractmethod
    def get_root_nodes(self, file_path: str) -> List[HierarchicalNode]:
        """Extract top-level hierarchical nodes from file."""
        pass
    
    @abstractmethod
    def get_child_nodes(self, parent_node: HierarchicalNode) -> List[HierarchicalNode]:
        """Get direct children of a node."""
        pass
    
    @abstractmethod
    def get_node_content(self, node: HierarchicalNode) -> str:
        """Extract searchable content from a node."""
        pass
    
    def search_in_node_subtree(self, node: HierarchicalNode, pattern: re.Pattern, 
                              include_descendants: bool = True) -> List[HierarchicalNode]:
        """Search within a node and optionally its descendants."""
        matches = []
        
        # Search current node
        node_content = self.get_node_content(node)
        if pattern.search(node_content):
            matches.append(node)
            if not include_descendants:
                return matches  # Early termination for context preservation
        
        # Search descendants if requested
        if include_descendants:
            for child in self.get_child_nodes(node):
                child_matches = self.search_in_node_subtree(child, pattern, include_descendants)
                if child_matches:
                    matches.extend(child_matches)
                    if not include_descendants:
                        break  # Early termination
        
        return matches
    
    def extract_tags(self, file_path: str) -> List[str]:
        """Extract tags from file (default implementation returns empty list)."""
        return []
    
    def generate_link(self, file_path: str, node_id: Optional[str] = None) -> str:
        """Generate appropriate link format for this file type."""
        link_format = self.link_config.get('format', '{path}')
        supports_fragments = self.link_config.get('supports_fragments', False)
        
        # Convert to relative path
        rel_path = Path(file_path).relative_to(Path.cwd())
        
        if supports_fragments and node_id:
            return link_format.format(path=str(rel_path), fragment=node_id, anchor=node_id)
        else:
            return link_format.format(path=str(rel_path))
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that file is compatible with this handler."""
        try:
            # Basic existence and extension check
            path = Path(file_path)
            if not path.exists():
                return False
            
            extensions = self.config.get('extensions', [])
            if extensions and path.suffix not in extensions:
                return False
            
            return True
        except Exception:
            return False


class HandlerRegistry:
    """Registry for file handlers."""
    
    def __init__(self):
        self._handlers: Dict[str, type] = {}
        self._instances: Dict[str, FileHandler] = {}
    
    def register_handler(self, name: str, handler_class: type):
        """Register a handler class."""
        self._handlers[name] = handler_class
    
    def get_handler(self, name: str, config: Dict[str, Any]) -> Optional[FileHandler]:
        """Get handler instance for the given name."""
        if name not in self._handlers:
            return None
        
        # Create instance if not cached
        if name not in self._instances:
            self._instances[name] = self._handlers[name](config)
        
        return self._instances[name]
    
    def get_handler_for_file(self, file_path: str, file_types_config: Dict[str, Any]) -> Optional[FileHandler]:
        """Find appropriate handler for a file."""
        for type_name, type_config in file_types_config.items():
            handler = self.get_handler(type_config['handler'], type_config)
            if handler and handler.can_handle(file_path):
                return handler
        return None
    
    def load_default_handlers(self):
        """Load default handlers."""
        # Import and register default handlers
        try:
            from handlers.freeplane_handler import FreeplaneHandler
            self.register_handler('FreeplaneHandler', FreeplaneHandler)
        except ImportError:
            pass
        
        try:
            from handlers.markdown_handler import MarkdownHandler
            self.register_handler('MarkdownHandler', MarkdownHandler)
        except ImportError:
            pass


# Global registry instance
handler_registry = HandlerRegistry()


def create_word_boundary_pattern(keyword: str) -> re.Pattern:
    """Create regex pattern with word boundaries (escapes regex chars)."""
    escaped_keyword = re.escape(keyword)
    
    # Check if keyword starts/ends with word characters
    starts_with_word_char = keyword and (keyword[0].isalnum() or keyword[0] == '_')
    ends_with_word_char = keyword and (keyword[-1].isalnum() or keyword[-1] == '_')
    
    # Build pattern with appropriate boundaries
    left_boundary = r'\b' if starts_with_word_char else r'(?<!\S)'  # whitespace or start
    right_boundary = r'\b' if ends_with_word_char else r'(?!\S)'   # whitespace or end
    
    return re.compile(rf'{left_boundary}{escaped_keyword}{right_boundary}', re.IGNORECASE)


def create_regex_pattern(pattern: str) -> re.Pattern:
    """Create regex pattern treating input as actual regex (no escaping)."""
    return re.compile(pattern, re.IGNORECASE)


def create_word_boundary_regex_pattern(pattern: str) -> re.Pattern:
    """Create regex pattern with word boundaries treating input as regex (no escaping)."""
    return re.compile(rf'\b(?:{pattern})\b', re.IGNORECASE)


def generate_unique_id() -> str:
    """Generate unique ID in Freeplane format."""
    import time
    import random
    
    # Generate timestamp-based ID similar to Freeplane format
    timestamp = int(time.time() * 1000)
    random_part = random.randint(1000, 9999)
    return f"ID_{timestamp:X}_{random_part:X}"


def get_current_timestamp() -> str:
    """Get current timestamp in Freeplane format (YYYYMMDDTHHMMSS)."""
    from datetime import datetime
    return datetime.now().strftime('%Y%m%dT%H%M%S')