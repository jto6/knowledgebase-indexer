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
        
        # First pass: identify all headings and list items with their positions
        line_elements = []  # Track what each line is
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if not stripped:
                line_elements.append(None)  # Empty line
                continue
            
            # Check for headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                
                line_elements.append({
                    'type': 'heading',
                    'level': level,
                    'text': heading_text,
                    'line_num': i + 1
                })
                continue
            
            # Check for list items
            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
            if list_match:
                indent = list_match.group(1)
                text = list_match.group(3)
                level = len(indent) // 2
                
                line_elements.append({
                    'type': 'list_item',
                    'level': level,
                    'text': text,
                    'line_num': i + 1
                })
                continue
            
            # Regular content
            line_elements.append({
                'type': 'content',
                'text': stripped,
                'line_num': i + 1
            })
        
        # Second pass: build all heading elements with proper content boundaries  
        for i, element in enumerate(line_elements):
            if not element or element['type'] != 'heading':
                continue
            
            # This is a heading - collect its content (only content that's not in subheadings)
            heading_level = element['level']
            heading_text = element['text']
            content_parts = [heading_text]
            
            # Look ahead for content that belongs directly to this heading (not subheadings)
            j = i + 1
            while j < len(line_elements):
                next_element = line_elements[j]
                
                if not next_element:  # Skip empty lines
                    j += 1
                    continue
                
                if next_element['type'] == 'heading':
                    # Stop if we hit ANY heading (subheadings will be processed separately)
                    break
                
                # Add direct content (paragraphs, but not list items which become separate nodes)
                if next_element['type'] == 'content':
                    content_parts.append(next_element['text'])
                
                j += 1
            
            # Create heading element
            elements.append(MarkdownElement(
                element_type='heading',
                level=heading_level,
                content=' '.join(content_parts),
                raw_text=heading_text,
                line_number=element['line_num']
            ))
        
        # Third pass: add all list items as separate elements
        for element in line_elements:
            if element and element['type'] == 'list_item':
                elements.append(MarkdownElement(
                    element_type='list_item',
                    level=element['level'],
                    content=element['text'],
                    raw_text=element['text'],
                    line_number=element['line_num']
                ))
        
        return elements
    
    def _build_composite_hierarchy(self, elements: List[MarkdownElement], 
                                 file_path: str) -> List[HierarchicalNode]:
        """Build composite hierarchy from parsed elements."""
        root_nodes = []
        heading_stack = []  # Stack to track heading hierarchy
        list_stack = []     # Stack to track list hierarchy within current heading
        
        for element in elements:
            if element.element_type == 'heading':
                # Pop headings of same or higher level
                while heading_stack and heading_stack[-1].metadata['heading_level'] >= element.level:
                    heading_stack.pop()
                
                # Clear list stack when entering new heading section
                list_stack = []
                
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
                # Determine parent node for this list item
                parent_node = None
                
                # Pop list items that are at same or higher level (shallower indentation)
                while list_stack and list_stack[-1].metadata.get('list_level', 0) >= element.level:
                    list_stack.pop()
                
                # Find parent: either a list item or the current heading
                if list_stack:
                    # Parent is the last list item (deeper indentation)
                    parent_node = list_stack[-1]
                elif heading_stack:
                    # Parent is the current heading section
                    parent_node = heading_stack[-1]
                
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
                
                # Add to appropriate parent
                if parent_node:
                    parent_node.add_child(list_node)
                else:
                    # No parent heading, add to root
                    root_nodes.append(list_node)
                
                # Add to list stack for potential children
                list_stack.append(list_node)
        
        return root_nodes
    
    def extract_tags(self, file_path: str) -> Dict[str, List[tuple]]:
        """Extract tags from Markdown file (R-MARKDOWN-TAG-001 to R-MARKDOWN-TAG-007)."""
        tag_map = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tags = set()

            # Extract hashtag-style tags (R-MARKDOWN-TAG-001)
            # Match hashtags that are standalone (after whitespace or start of line)
            hashtag_pattern = r'(?:^|\s)#([\w-]+)(?=\s|[^\w-]|$)'
            
            # Remove code blocks to avoid extracting hashtags from code
            # Remove fenced code blocks (```...```)
            content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
            # Remove inline code (`...`)
            content_no_code = re.sub(r'`[^`\n]+`', '', content_no_code)
            
            hashtag_matches = re.findall(hashtag_pattern, content_no_code, re.MULTILINE)
            
            # Filter out common false positives and pure numbers
            excluded_patterns = {
                'define', 'include', 'ifndef', 'endif', 'pragma', 'undef',
                'if', 'else', 'error', 'warning', 'line'  # C preprocessor directives
            }
            
            filtered_tags = []
            for tag in hashtag_matches:
                if not tag.isdigit() and tag.lower() not in excluded_patterns:
                    filtered_tags.append(tag)
            
            tags.update(filtered_tags)

            # Extract YAML frontmatter tags (R-MARKDOWN-TAG-002)
            yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if yaml_match:
                frontmatter = yaml_match.group(1)
                tag_matches = re.findall(r'^tags?:\s*(.+)$', frontmatter, re.MULTILINE | re.IGNORECASE)
                for tag_line in tag_matches:
                    # Handle both YAML list format and comma-separated (R-MARKDOWN-TAG-003, R-MARKDOWN-TAG-004)
                    if tag_line.startswith('[') and tag_line.endswith(']'):
                        # YAML list format: [tag1, tag2, tag3]
                        tag_content = tag_line[1:-1]
                        tag_values = [tag.strip().strip('"\'') for tag in tag_content.split(',')]
                    else:
                        # Comma-separated format
                        tag_values = [tag.strip() for tag in tag_line.split(',')]

                    # Strip quotes and whitespace (R-MARKDOWN-TAG-005)
                    tags.update(filter(None, tag_values))

            # Combine hashtag and frontmatter tags into unified tag list (R-MARKDOWN-TAG-006)
            # Associate tags with file-level context for linking (R-MARKDOWN-TAG-007)
            for tag in tags:
                tag = tag.strip()
                if tag:
                    if tag not in tag_map:
                        tag_map[tag] = []
                    # For markdown, use empty node_id since tags are file-level
                    # Use filename as node_text for display
                    tag_map[tag].append((file_path, '', Path(file_path).name))

        except Exception as e:
            print(f"Error extracting tags from {file_path}: {e}")

        return tag_map

    def generate_link(self, file_path: str, node_id: Optional[str] = None) -> str:
        """Generate link with optional GitHub-style anchor."""
        rel_path = Path(file_path).relative_to(Path.cwd())
        
        if node_id:
            # For markdown, we need to convert node info to GitHub-style anchor
            # The node_id from KBI is meaningless to markdown viewers
            # We need the actual heading text to create a proper anchor
            return f"{rel_path}#{node_id}"  # This will be fixed by generate_markdown_anchor
        else:
            return str(rel_path)
    
    def generate_markdown_anchor(self, heading_text: str) -> str:
        """Generate GitHub-style anchor from heading text."""
        if not heading_text:
            return ""
        
        # Convert to lowercase and replace spaces/special chars with dashes
        # GitHub style: "ARM Interrupt Handling" -> "arm-interrupt-handling"
        anchor = heading_text.lower()
        
        # Replace spaces and common punctuation with dashes
        anchor = re.sub(r'[^\w\-_]', '-', anchor)
        
        # Remove multiple consecutive dashes
        anchor = re.sub(r'-+', '-', anchor)
        
        # Remove leading/trailing dashes
        anchor = anchor.strip('-')
        
        return anchor
    
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
