#!/usr/bin/env python3
"""Markdown file handler with composite hierarchy support."""

import re
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core_handlers import FileHandler, HierarchicalNode, generate_unique_id


@dataclass
class MarkdownElement:
    """Represents a parsed markdown element."""
    element_type: str  # 'heading', 'list_item', 'paragraph', 'code_block'
    level: int  # heading level or list nesting level
    content: str
    raw_text: str
    line_number: int
    children: List['MarkdownElement'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class MarkdownHandler(FileHandler):
    """Handler for Markdown files with composite hierarchy."""
    
    def can_handle(self, file_path: str) -> bool:
        """Check if this handler can process the given file."""
        path = Path(file_path)
        return (path.suffix in self.config.get('extensions', ['.md', '.markdown']) and 
                path.exists())
    
    def get_root_nodes(self, file_path: str) -> List[HierarchicalNode]:
        """Extract hierarchical nodes from Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse markdown into elements
            elements = self._parse_markdown(content)
            
            # Build composite hierarchy
            root_nodes = self._build_composite_hierarchy(elements, file_path)
            
            return root_nodes
            
        except Exception as e:
            print(f"Error parsing Markdown file {file_path}: {e}")
            return []
    
    def get_child_nodes(self, parent_node: HierarchicalNode) -> List[HierarchicalNode]:
        """Get direct children of a node."""
        return parent_node.children
    
    def get_node_content(self, node: HierarchicalNode) -> str:
        """Extract searchable content from a node."""
        if node.node_type == 'heading':
            # For heading nodes, include heading text plus section content
            return node.content
        elif node.node_type == 'list_item':
            return node.text
        else:
            return node.content
    
    def _parse_markdown(self, content: str) -> List[MarkdownElement]:
        """Parse markdown content into structured elements."""
        elements = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                i += 1
                continue
            
            # Parse headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                
                # Collect content until next heading of same or higher level
                section_content = [text]
                j = i + 1
                
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    
                    next_heading_match = re.match(r'^(#{1,6})\s+', next_line)
                    if next_heading_match:
                        next_level = len(next_heading_match.group(1))
                        if next_level <= level:
                            break
                    
                    section_content.append(lines[j])
                    j += 1
                
                elements.append(MarkdownElement(
                    element_type='heading',
                    level=level,
                    content=' '.join(section_content),
                    raw_text=text,
                    line_number=i + 1
                ))
                
                i = j
                continue
            
            # Parse list items
            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
            if list_match:
                indent = list_match.group(1)
                marker = list_match.group(2)
                text = list_match.group(3)
                level = len(indent) // 2  # Assuming 2-space indentation
                
                elements.append(MarkdownElement(
                    element_type='list_item',
                    level=level,
                    content=text,
                    raw_text=text,
                    line_number=i + 1
                ))
                
                i += 1
                continue
            
            # Regular paragraph or other content
            elements.append(MarkdownElement(
                element_type='paragraph',
                level=0,
                content=stripped,
                raw_text=stripped,
                line_number=i + 1
            ))
            
            i += 1
        
        return elements
    
    def _build_composite_hierarchy(self, elements: List[MarkdownElement], 
                                 file_path: str) -> List[HierarchicalNode]:
        """Build composite hierarchy from parsed elements."""
        root_nodes = []
        heading_stack = []  # Stack to track heading hierarchy
        
        for element in elements:
            if element.element_type == 'heading':
                # Pop headings of same or higher level
                while heading_stack and heading_stack[-1].metadata['heading_level'] >= element.level:
                    heading_stack.pop()
                
                # Create heading node
                heading_node = HierarchicalNode(
                    id=generate_unique_id(),
                    content=element.content,
                    text=element.raw_text,
                    file_path=file_path,
                    node_type='heading',
                    metadata={
                        'heading_level': element.level,
                        'line_number': element.line_number
                    }
                )
                
                # Add to parent or root
                if heading_stack:
                    heading_stack[-1].add_child(heading_node)
                else:
                    root_nodes.append(heading_node)
                
                heading_stack.append(heading_node)
            
            elif element.element_type == 'list_item':
                # Find the appropriate parent (closest heading or list item)
                parent_node = None
                
                if heading_stack:
                    parent_node = heading_stack[-1]
                    
                    # Look for existing list structure within this heading
                    existing_lists = parent_node.find_children_by_type('list_item')
                    
                    if existing_lists:
                        # Find appropriate parent based on indentation level
                        for list_node in reversed(existing_lists):
                            if list_node.metadata.get('list_level', 0) < element.level:
                                parent_node = list_node
                                break
                
                # Create list item node
                list_node = HierarchicalNode(
                    id=generate_unique_id(),
                    content=element.content,
                    text=element.raw_text,
                    file_path=file_path,
                    node_type='list_item',
                    metadata={
                        'list_level': element.level,
                        'line_number': element.line_number
                    }
                )
                
                if parent_node:
                    parent_node.add_child(list_node)
                else:
                    root_nodes.append(list_node)
        
        return root_nodes
    
    def extract_tags(self, file_path: str) -> List[str]:
        """Extract tags from Markdown file."""
        tags = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract hashtag-style tags
            hashtag_matches = re.findall(r'#(\w+)', content)
            tags.update(hashtag_matches)
            
            # Extract YAML frontmatter tags
            yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if yaml_match:
                frontmatter = yaml_match.group(1)
                tag_matches = re.findall(r'^tags?:\s*(.+)$', frontmatter, re.MULTILINE | re.IGNORECASE)
                for tag_line in tag_matches:
                    # Handle both YAML list format and comma-separated
                    if tag_line.startswith('[') and tag_line.endswith(']'):
                        # YAML list format: [tag1, tag2, tag3]
                        tag_content = tag_line[1:-1]
                        tag_values = [tag.strip().strip('"\'') for tag in tag_content.split(',')]
                    else:
                        # Comma-separated format
                        tag_values = [tag.strip() for tag in tag_line.split(',')]
                    
                    tags.update(filter(None, tag_values))
            
        except Exception as e:
            print(f"Error extracting tags from {file_path}: {e}")
        
        return sorted(list(tags))
    
    def generate_link(self, file_path: str, node_id: Optional[str] = None) -> str:
        """Generate link with optional anchor."""
        rel_path = Path(file_path).relative_to(Path.cwd())
        
        if node_id:
            # For markdown, create anchor from heading text
            return f"{rel_path}#{node_id}"
        else:
            return str(rel_path)
    
    def search_in_node_subtree(self, node: HierarchicalNode, pattern: re.Pattern, 
                              include_descendants: bool = True) -> List[HierarchicalNode]:
        """Search within a node and optionally its descendants."""
        matches = []
        
        # Search current node content
        node_content = self.get_node_content(node)
        if pattern.search(node_content):
            matches.append(node)
            if not include_descendants:
                return matches  # Early termination for context preservation
        
        # Search descendants if requested
        if include_descendants or not matches:
            for child in node.children:
                child_matches = self.search_in_node_subtree(child, pattern, include_descendants)
                if child_matches:
                    matches.extend(child_matches)
                    if not include_descendants and matches:
                        break  # Early termination to preserve hierarchical context
        
        return matches