#!/usr/bin/env python3
"""Freeplane .mm file handler implementation."""

import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from pathlib import Path
import html
import re

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core_handlers import FileHandler, HierarchicalNode, generate_unique_id


class FreeplaneHandler(FileHandler):
    """Handler for Freeplane mind map (.mm) files."""
    
    def can_handle(self, file_path: str) -> bool:
        """Check if this handler can process the given file."""
        path = Path(file_path)
        return (path.suffix in self.config.get('extensions', ['.mm']) and 
                path.exists() and 
                self._is_valid_freeplane_file(file_path))
    
    def _is_valid_freeplane_file(self, file_path: str) -> bool:
        """Check if file is a valid Freeplane XML file."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            return root.tag == 'map'
        except ET.ParseError:
            return False
        except Exception:
            return False
    
    def get_root_nodes(self, file_path: str) -> List[HierarchicalNode]:
        """Extract top-level hierarchical nodes from Freeplane file."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find the root node element
            root_node_element = root.find('.//node')
            if root_node_element is None:
                return []
            
            root_node = self._xml_element_to_hierarchical_node(root_node_element, file_path)
            return [root_node]
            
        except Exception as e:
            print(f"Error parsing Freeplane file {file_path}: {e}")
            return []
    
    def get_child_nodes(self, parent_node: HierarchicalNode) -> List[HierarchicalNode]:
        """Get direct children of a node."""
        return parent_node.children
    
    def get_node_content(self, node: HierarchicalNode) -> str:
        """Extract searchable content from a node."""
        content_parts = [node.text, node.content]

        # Include rich content if available
        if 'richcontent' in node.metadata:
            content_parts.append(node.metadata['richcontent'])

        # Include note content if available
        if 'note' in node.metadata:
            content_parts.append(node.metadata['note'])

        return ' '.join(filter(None, content_parts))

    def _xml_element_to_hierarchical_node(self, element: ET.Element, file_path: str, 
                                        parent: Optional[HierarchicalNode] = None) -> HierarchicalNode:
        """Convert XML element to HierarchicalNode."""
        node_id = element.get('ID', generate_unique_id())
        text = element.get('TEXT', '')
        
        # Decode HTML entities in text
        if text:
            text = html.unescape(text)
        
        # Extract rich content
        richcontent_elem = element.find('.//richcontent[@TYPE="NODE"]/html/body')
        richcontent = ""
        if richcontent_elem is not None:
            richcontent = self._extract_text_from_html(richcontent_elem)
        
        # Extract note content
        note_elem = element.find('.//richcontent[@TYPE="NOTE"]/html/body')
        note_content = ""
        if note_elem is not None:
            note_content = self._extract_text_from_html(note_elem)
        
        # Combine all content
        all_content = ' '.join(filter(None, [text, richcontent, note_content]))
        
        # Create hierarchical node
        node = HierarchicalNode(
            id=node_id,
            content=all_content,
            text=text,
            file_path=file_path,
            parent=parent,
            node_type="freeplane_node",
            metadata={
                'richcontent': richcontent,
                'note': note_content,
                'xml_element': element,
                'created': element.get('CREATED', ''),
                'modified': element.get('MODIFIED', '')
            }
        )
        
        # Process child nodes
        child_elements = element.findall('./node')
        for child_element in child_elements:
            child_node = self._xml_element_to_hierarchical_node(child_element, file_path, node)
            node.add_child(child_node)
        
        return node
    
    def _extract_text_from_html(self, element: ET.Element) -> str:
        """Extract text content from HTML elements."""
        text_parts = []

        # Get text content
        if element.text:
            text_parts.append(element.text.strip())

        # Recursively process child elements
        for child in element:
            text_parts.append(self._extract_text_from_html(child))
            if child.tail:
                text_parts.append(child.tail.strip())

        return ' '.join(filter(None, text_parts))

    def extract_tags(self, file_path: str) -> Dict[str, List[tuple]]:
        """Extract tags from Freeplane node TAGS attributes (R-TAG-001 to R-TAG-004)."""
        tag_map = {}

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find all nodes with TAGS attribute (R-TAG-001)
            for node_elem in root.findall('.//node[@TAGS]'):
                tags_attr = node_elem.get('TAGS', '')
                if tags_attr:
                    # Handle HTML entities and encoded characters (R-TAG-002)
                    decoded = html.unescape(tags_attr)

                    # Replace encoded newlines with spaces (R-TAG-003)
                    decoded = decoded.replace('&#xa;', ' ')

                    # Split on whitespace to extract individual tags (R-TAG-004)
                    individual_tags = decoded.split()

                    for tag in individual_tags:
                        tag = tag.strip()
                        if tag:
                            node_id = node_elem.get('ID', '')
                            node_text = node_elem.get('TEXT', '')

                            if tag not in tag_map:
                                tag_map[tag] = []
                            tag_map[tag].append((file_path, node_id, node_text))

        except Exception as e:
            print(f"Error extracting tags from {file_path}: {e}")

        return tag_map

    def generate_link(self, file_path: str, node_id: Optional[str] = None) -> str:
        """Generate link with optional node fragment."""
        rel_path = Path(file_path).relative_to(Path.cwd())

        if node_id:
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
                    if not include_descendants:
                        break  # Early termination to preserve hierarchical context

        return matches
