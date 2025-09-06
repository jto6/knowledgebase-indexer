#!/usr/bin/env python3
"""XML mind map generator for Freeplane-compatible output."""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from collections import defaultdict
import os

from core_handlers import generate_unique_id, get_current_timestamp, HierarchicalNode
from search import SearchResult
from keywords import KeywordEntry


class FreeplaneMapGenerator:
    """Generates Freeplane-compatible mind map XML files."""
    
    def __init__(self, output_path: str):
        """Initialize generator with output path."""
        self.output_path = Path(output_path)
        self.used_ids: Set[str] = set()
        self.node_counter = 0
    
    def _generate_unique_id(self) -> str:
        """Generate unique ID ensuring no duplicates."""
        while True:
            node_id = generate_unique_id()
            if node_id not in self.used_ids:
                self.used_ids.add(node_id)
                return node_id
    
    def create_mind_map(self, file_system_index: Dict[str, List[HierarchicalNode]],
                       keyword_entries: List[Any],
                       tag_results: Dict[str, List[tuple]],
                       config: Dict[str, Any]) -> str:
        """Create complete mind map with all three indexes."""
        
        # Create root map element matching actual Freeplane format
        root = ET.Element('map', {
            'version': 'freeplane 1.12.1'
        })
        
        # Create main root node
        main_root = ET.SubElement(root, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'Navigation Index'
        })
        
        # Add file system index
        if file_system_index:
            fs_node = self._create_file_system_index(main_root, file_system_index)
        
        # Add keyword index
        if keyword_entries:
            kw_node = self._create_keyword_index(main_root, keyword_entries)
        
        # Add tag index (only if tags found) (R-TAG-005)
        if tag_results:
            tag_node = self._create_tag_index(main_root, tag_results)
        
        # Generate pretty-printed XML
        xml_content = self._prettify_xml(root)
        
        # Write to file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return str(self.output_path)
    
    def _create_file_system_index(self, parent: ET.Element, 
                                file_system_index: Dict[str, List[HierarchicalNode]]) -> ET.Element:
        """Create file system navigation index."""
        fs_root = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'File System Index'
        })
        
        # Group files by directory
        dir_structure = self._build_directory_structure(list(file_system_index.keys()))
        
        # Create directory hierarchy
        self._create_directory_nodes(fs_root, dir_structure, file_system_index)
        
        return fs_root
    
    def _build_directory_structure(self, file_paths: List[str]) -> Dict[str, Any]:
        """Build nested directory structure from file paths, excluding common path prefix (R-FS-007)."""
        if not file_paths:
            return {}
        
        # Find common path prefix (R-FS-007)
        common_prefix_parts = self._find_common_path_prefix(file_paths)
        
        structure = {}
        
        for file_path in sorted(file_paths):
            path = Path(file_path)
            parts = path.parts
            
            # Remove common prefix from parts (R-FS-007)
            if len(common_prefix_parts) > 0:
                parts = parts[len(common_prefix_parts):]
            
            # Build directory structure with remaining parts
            current = structure
            for part in parts[:-1]:  # All except filename
                if part not in current:
                    current[part] = {'_dirs': {}, '_files': []}
                # Navigate to the _dirs level for the next iteration
                current = current[part]['_dirs']
            
            # Now current is the '_dirs' dict of the final directory
            # We need to go back one level to add the file to the directory itself
            if len(parts) > 1:
                # Navigate back to the parent directory to add the file
                parent = structure
                for part in parts[:-2]:  # All except last two (dir and filename)
                    parent = parent[part]['_dirs']
                final_dir = parent[parts[-2]]  # The actual directory containing the file
                final_dir['_files'].append(str(path))
            else:
                # File is at root level
                if '_files' not in structure:
                    structure['_files'] = []
                structure['_files'].append(str(path))
        
        return structure
    
    def _find_common_path_prefix(self, file_paths: List[str]) -> tuple:
        """Find common directory path prefix among all file paths (R-FS-007)."""
        if not file_paths:
            return ()
        
        # Convert all paths to Path objects and get their parent directories
        dir_paths = [Path(file_path).parent for file_path in file_paths]
        
        # Convert to parts tuples for comparison
        path_parts_list = [path.parts for path in dir_paths]
        
        if not path_parts_list:
            return ()
        
        # Find common prefix by comparing parts
        common_parts = []
        min_length = min(len(parts) for parts in path_parts_list)
        
        for i in range(min_length):
            # Get the part at position i from the first path
            candidate_part = path_parts_list[0][i]
            
            # Check if all paths have the same part at this position
            if all(parts[i] == candidate_part for parts in path_parts_list):
                common_parts.append(candidate_part)
            else:
                break
        
        return tuple(common_parts)
    
    def _create_directory_nodes(self, parent: ET.Element, structure: Dict[str, Any],
                              file_index: Dict[str, List[HierarchicalNode]]):
        """Recursively create directory and file nodes."""
        # Create directory nodes first (sorted)
        for dir_name in sorted(structure.keys()):
            if dir_name.startswith('_'):
                continue
            
            dir_data = structure[dir_name]
            
            # Skip empty directories
            if not dir_data.get('_dirs') and not dir_data.get('_files'):
                continue
            
            dir_node = ET.SubElement(parent, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': dir_name
            })
            
            # Recurse into subdirectories
            if '_dirs' in dir_data:
                self._create_directory_nodes(dir_node, dir_data['_dirs'], file_index)
            
            # Add files in this directory
            if '_files' in dir_data:
                for file_path in sorted(dir_data['_files']):
                    # Skip the output file itself
                    if Path(file_path).resolve() == self.output_path.resolve():
                        continue
                    
                    self._create_file_node(dir_node, file_path, file_index.get(file_path, []))
    
    def _create_file_node(self, parent: ET.Element, file_path: str, 
                         nodes: List[HierarchicalNode]):
        """Create node for a single file."""
        file_name = Path(file_path).name
        
        # Handle paths that may be outside current working directory
        try:
            rel_path = Path(file_path).relative_to(Path.cwd())
            link_path = str(rel_path)
        except ValueError:
            # File is outside current working directory, use absolute path
            link_path = file_path
        
        file_node = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': file_name,
            'LINK': link_path
        })
        
        # Add hierarchical content from file
        for node in nodes:
            self._create_hierarchical_node(file_node, node, link_path)
    
    def _create_hierarchical_node(self, parent: ET.Element, node: HierarchicalNode, 
                                base_file_path: str):
        """Create XML node from HierarchicalNode."""
        # Determine link
        link = base_file_path
        if hasattr(node, 'id') and node.id:
            link += f"#{node.id}"
        
        xml_node = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': node.text or node.content[:100] + "..." if len(node.content) > 100 else node.content,
            'LINK': link
        })
        
        # Add children recursively
        for child in node.children:
            self._create_hierarchical_node(xml_node, child, base_file_path)
    
    def _create_keyword_index(self, parent: ET.Element, 
                            keyword_entries: List[Any]) -> ET.Element:
        """Create keyword index preserving exact hierarchical structure from keyword file."""
        kw_root = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'Keyword Index'
        })
        
        # Build tree structure directly from keyword entries (sorted alphabetically)
        sorted_entries = sorted(keyword_entries, key=lambda e: e.text.lower())
        for entry in sorted_entries:
            self._create_keyword_entry_node(kw_root, entry)
        
        return kw_root
    
    def _create_keyword_entry_node(self, parent: ET.Element, entry: Any) -> ET.Element:
        """Create a node for a keyword entry, preserving hierarchy."""
        # Create node for this entry
        entry_node = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': entry.text
        })
        
        if entry.is_leaf and hasattr(entry, 'search_results') and entry.search_results:
            # This is a leaf node with search results - add file/match children
            self._add_search_results_to_node(entry_node, entry.search_results)
        
        # Add children (for both leaf and interior nodes, preserve structure, sorted alphabetically)
        sorted_children = sorted(entry.children, key=lambda e: e.text.lower())
        for child_entry in sorted_children:
            self._create_keyword_entry_node(entry_node, child_entry)
        
        return entry_node
    
    def _add_search_results_to_node(self, parent: ET.Element, search_results: Dict[str, List[Any]]):
        """Add search results as children of a keyword node."""
        for file_path, results in search_results.items():
            if not results:
                continue
            
            file_name = Path(file_path).name
            
            # Handle paths that may be outside current working directory
            try:
                rel_path = Path(file_path).relative_to(Path.cwd())
                link_path = str(rel_path)
            except ValueError:
                # File is outside current working directory, use absolute path
                link_path = file_path
            
            file_node = ET.SubElement(parent, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': file_name,
                'LINK': link_path
            })
            
            # Add individual matches
            for result in results:
                match_text = result.node.text or result.matched_content[:100]
                if len(match_text) > 100:
                    match_text = match_text[:100] + "..."
                
                link = link_path
                if hasattr(result.node, 'id') and result.node.id:
                    link += f"#{result.node.id}"
                
                ET.SubElement(file_node, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': match_text,
                    'LINK': link
                })
    
    def _create_tag_index(self, parent: ET.Element, 
                         tag_results: Dict[str, List[tuple]]) -> ET.Element:
        """Create tag-based navigation index (R-TAG-005 to R-TAG-012)."""
        tag_root = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'Tag Index'
        })
        
        # Sort tags alphabetically at top level (R-TAG-006)
        for tag in sorted(tag_results.keys(), key=str.lower):
            tag_node = ET.SubElement(tag_root, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': tag
            })
            
            # Group matches by file (R-TAG-009)
            file_groups = {}
            for file_path, node_id, node_text in tag_results[tag]:
                if file_path not in file_groups:
                    file_groups[file_path] = []
                file_groups[file_path].append((node_id, node_text))
            
            # Sort files alphabetically within each tag group (R-TAG-007)
            for file_path in sorted(file_groups.keys(), key=lambda x: Path(x).name.lower()):
                file_name = Path(file_path).name
                
                # Handle paths that may be outside current working directory
                try:
                    rel_path = Path(file_path).relative_to(Path.cwd())
                    link_path = str(rel_path)
                except ValueError:
                    # File is outside current working directory, use absolute path
                    link_path = file_path
                
                # Create hyperlinks to files at file level (R-TAG-010)
                file_node = ET.SubElement(tag_node, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': file_name,
                    'LINK': link_path
                })
                
                # Sort individual node matches alphabetically within each file (R-TAG-008)
                sorted_matches = sorted(file_groups[file_path], key=lambda x: x[1].lower())
                
                # Create fragment hyperlinks to individual nodes (R-TAG-011)
                for node_id, node_text in sorted_matches:
                    match_node = ET.SubElement(file_node, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': node_text,
                        'LINK': f"{link_path}#{node_id}"
                    })
        
        return tag_root
    
    def _prettify_xml(self, root: ET.Element) -> str:
        """Convert XML element to pretty-printed string."""
        rough_string = ET.tostring(root, encoding='unicode', method='xml')
        
        # Parse and pretty-print
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", newl="\n")
        
        # Remove empty lines and clean up
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        
        # Remove the XML declaration line (minidom adds it)
        if lines and lines[0].startswith('<?xml'):
            lines = lines[1:]
        
        # Match existing Freeplane format - no XML declaration
        xml_content = '\n'.join(lines)
        
        return xml_content


def create_sample_mindmap(output_path: str = "sample_index.mm"):
    """Create a sample mind map for testing."""
    generator = FreeplaneMapGenerator(output_path)
    
    # Sample data
    file_system_index = {
        "README.md": [],
        "src/main.py": [],
        "docs/guide.md": []
    }
    
    keyword_results = {}
    tag_results = {}
    config = {}
    
    result_path = generator.create_mind_map(file_system_index, keyword_results, 
                                          tag_results, config)
    
    print(f"Sample mind map created: {result_path}")
    return result_path