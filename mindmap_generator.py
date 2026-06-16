#!/usr/bin/env python3
"""XML mind map generator for Freeplane-compatible output."""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from collections import defaultdict
import os
import re

from core_handlers import generate_unique_id, get_current_timestamp, HierarchicalNode
from search import SearchResult
from keywords import KeywordEntry
from word_filter import SignificantWordFilter


class FreeplaneMapGenerator:
    """Generates Freeplane-compatible mind map XML files."""
    
    def __init__(self, output_path: str):
        """Initialize generator with output path."""
        self.output_path = Path(output_path)
        self.used_ids: Set[str] = set()
        self.node_counter = 0
        self._card_essence_map: Dict[str, str] = {}  # card_path -> essence
    
    def _generate_unique_id(self) -> str:
        """Generate unique ID ensuring no duplicates."""
        while True:
            node_id = generate_unique_id()
            if node_id not in self.used_ids:
                self.used_ids.add(node_id)
                return node_id
    
    def _generate_markdown_anchor(self, heading_text: str) -> str:
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
    
    def _find_markdown_anchor_for_node(self, node: HierarchicalNode) -> str:
        """Find the appropriate GitHub-style anchor for a markdown node."""
        h = self._find_markdown_heading_node(node)
        return self._generate_markdown_anchor(h.text or '') if h else ""

    def _find_markdown_heading_node(self, node: HierarchicalNode):
        """Return the nearest heading ancestor (or self) for a markdown node, or None."""
        if hasattr(node, 'node_type') and node.node_type == 'heading':
            return node
        current = node
        while current and hasattr(current, 'parent') and current.parent:
            current = current.parent
            if hasattr(current, 'node_type') and current.node_type == 'heading':
                return current
        return None
    
    def create_mind_map(self, file_system_index: Dict[str, List[HierarchicalNode]],
                       keyword_entries: List[Any],
                       tag_results: Dict[str, List[tuple]],
                       word_results: Dict[str, Dict],
                       config: Dict[str, Any]) -> str:
        """Create complete mind map with all four indexes."""
        
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
        
        # Add word index (only if words found) (R-WORD-001)
        if word_results:
            word_node = self._create_word_index(main_root, word_results)
        
        # Generate pretty-printed XML
        xml_content = self._prettify_xml(root)
        
        # Write to file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return str(self.output_path)

    def render_model(self, model, config: Dict[str, Any]) -> str:
        """Render the unified index model (D16).

        Domains partition the top level when present; otherwise the views render
        directly under the root, byte-identical to the unpartitioned behavior.
        Each non-empty, non-suppressed view becomes a branch.
        """
        root = ET.Element('map', {'version': 'freeplane 1.12.1'})
        main_root = ET.SubElement(root, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'Navigation Index'
        })

        if model.partitioned:
            all_domains = list(model.ordered_domains())
            if len(all_domains) > 1:
                # Global aggregated views at top level for cross-domain search
                merged_di = self._merge_domain_indexes(model)
                self._render_domain_views(main_root, merged_di, config)
                # Per-domain drill-down under a "Domains" branch
                domains_node = ET.SubElement(main_root, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': 'Domains',
                })
                for name, di in all_domains:
                    dom_node = ET.SubElement(domains_node, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': f'Domain: {name}'
                    })
                    self._render_domain_views(dom_node, di, config)
            else:
                name, di = all_domains[0]
                dom_node = ET.SubElement(main_root, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': f'Domain: {name}'
                })
                self._render_domain_views(dom_node, di, config)
        else:
            di = model.domains.get(None)
            if di is not None:
                self._render_domain_views(main_root, di, config)

        xml_content = self._prettify_xml(root)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        return str(self.output_path)

    def _render_domain_views(self, parent: ET.Element, di, config: Dict[str, Any]):
        """Render every non-empty, non-suppressed view for one domain under `parent`."""
        from index_model import (view_enabled, VIEW_FILE_SYSTEM, VIEW_KEYWORD,
                                 VIEW_TAG, VIEW_WORD, VIEW_DEPENDENCIES, VIEW_GLOSSARY)
        r = 'freeplane'

        # Build card_path -> essence and card_path -> source_path lookups.
        self._card_essence_map = {}
        self._card_source_map = {}  # card_path -> source_path
        for source_path, group in getattr(di, 'card_groups', {}).items():
            for _label, card_path, card_essence in group.cards:
                if card_essence:
                    self._card_essence_map[card_path] = card_essence
                self._card_source_map[card_path] = source_path

        if (di.file_system or di.card_groups) and view_enabled(config, VIEW_FILE_SYSTEM, r):
            self._create_file_system_index(parent, di.file_system,
                                           getattr(di, 'card_groups', {}),
                                           getattr(di, 'dir_annotations', {}))
        if di.keyword_entries and view_enabled(config, VIEW_KEYWORD, r):
            self._create_keyword_index(parent, di.keyword_entries)
        if di.tags and view_enabled(config, VIEW_TAG, r):
            self._create_tag_index(parent, di.tags)
        if di.words and view_enabled(config, VIEW_WORD, r):
            self._create_word_index(parent, di.words)
        if di.dependencies and view_enabled(config, VIEW_DEPENDENCIES, r):
            self._create_dependencies_index(parent, di.dependencies)
        if di.glossary and view_enabled(config, VIEW_GLOSSARY, r):
            self._create_glossary_index(parent, di.glossary)

    def _linked_node(self, parent: ET.Element, text: str, link: str = None) -> ET.Element:
        """A node with TEXT and an optional LINK (relative to cwd when possible)."""
        attrs = {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': text,
        }
        if link:
            try:
                attrs['LINK'] = str(Path(link).relative_to(Path.cwd()))
            except ValueError:
                attrs['LINK'] = str(link)
        return ET.SubElement(parent, 'node', attrs)

    def _create_dependencies_index(self, parent: ET.Element, dependencies) -> ET.Element:
        """Dependencies view: each card → links to the cards it builds on."""
        dep_root = self._linked_node(parent, 'Dependencies')
        for rec, targets in sorted(dependencies, key=lambda d: (d[0].get('title') or '').lower()):
            label = rec.get('title') or Path(rec.get('file_path', '')).name
            card_node = self._linked_node(dep_root, label, rec.get('file_path'))
            for tlabel, tpath in targets:
                self._linked_node(card_node, f'builds on: {tlabel}', tpath)
        return dep_root

    def _create_glossary_index(self, parent: ET.Element, glossary) -> ET.Element:
        """Glossary view: defined term → link to its defining card."""
        gloss_root = self._linked_node(parent, 'Glossary')
        for term in sorted(glossary, key=str.lower):
            rec = glossary[term]
            self._linked_node(gloss_root, f'{term} — {rec.get("title") or ""}', rec.get('file_path'))
        return gloss_root

    def _create_file_system_index(self, parent: ET.Element,
                                file_system_index: Dict[str, List[HierarchicalNode]],
                                card_groups=None, dir_annotations=None) -> ET.Element:
        """Create file system navigation index.

        Non-card files appear as leaf nodes (unchanged). Cards are grouped under
        their source path: the source node is annotated with an essence when
        available, and topic cards appear as children (D21). Directory nodes are
        annotated with dir_summary essence when available.
        """
        if card_groups is None:
            card_groups = {}
        if dir_annotations is None:
            dir_annotations = {}
        fs_root = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'File System Index'
        })

        all_paths = list(file_system_index.keys()) + list(card_groups.keys())
        common_prefix_parts = self._find_common_path_prefix(all_paths)
        abs_base = str(Path(*common_prefix_parts)) if common_prefix_parts else "/"
        dir_structure = self._build_directory_structure(all_paths)
        self._create_directory_nodes(fs_root, dir_structure, file_system_index, card_groups,
                                     dir_annotations=dir_annotations, current_abs_dir=abs_base)
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
        """Return the home directory prefix to strip from file paths (R-FS-007).

        Only the home directory is stripped so that project/subdirectory structure
        remains visible in the tree (e.g. /home/jon/dev/proj → dev/proj/...).
        """
        if not file_paths:
            return ()

        home = Path.home()
        home_parts = home.parts  # e.g. ('/', 'home', 'jon')

        # Only strip the home prefix if every path lives under home.
        if all(Path(fp).parts[:len(home_parts)] == home_parts for fp in file_paths):
            return home_parts

        return ()

    def _display_path(self, file_path: str) -> str:
        """Return a display path with the home directory stripped and .kb/ collapsed.

        Strips the home directory prefix, then replaces the hidden /.kb/ directory
        segment with a ':' separator so card paths like dev/proj/.kb/card.kb.md
        render as dev/proj:card.kb.md.
        """
        path = Path(file_path)
        home_parts = Path.home().parts
        if path.parts[:len(home_parts)] == home_parts:
            remaining = path.parts[len(home_parts):]
            result = str(Path(*remaining)) if remaining else file_path
        else:
            result = file_path
        return result.replace('/.kb/', '::')

    def _merge_keyword_entries(self, all_entries_lists):
        """Merge keyword entry lists from multiple domains, deduplicating by text."""
        seen = {}
        for entries in all_entries_lists:
            for entry in entries:
                if entry.text not in seen:
                    seen[entry.text] = entry
                else:
                    existing = seen[entry.text]
                    if hasattr(entry, 'search_results') and entry.search_results:
                        if not hasattr(existing, 'search_results'):
                            existing.search_results = {}
                        for fp, results in entry.search_results.items():
                            existing.search_results.setdefault(fp, []).extend(results)
                    if entry.children:
                        existing.children = self._merge_keyword_entries(
                            [existing.children, entry.children]
                        )
        return list(seen.values())

    def _merge_domain_indexes(self, model):
        """Return a synthetic DomainIndex merging all domains for global views."""
        from index_model import DomainIndex
        merged = DomainIndex(name=None)
        domain_kw_lists = []
        for di in model.domains.values():
            merged.file_system.update(di.file_system)
            merged.card_groups.update(di.card_groups)
            merged.dir_annotations.update(di.dir_annotations)
            domain_kw_lists.append(di.keyword_entries)
            for tag, matches in di.tags.items():
                merged.tags.setdefault(tag, []).extend(matches)
            for word, file_matches in di.words.items():
                if isinstance(file_matches, dict):
                    merged.words.setdefault(word, {}).update(file_matches)
                else:
                    merged.words.setdefault(word, []).extend(file_matches)
            merged.dependencies.extend(di.dependencies)
            merged.glossary.update(di.glossary)
        merged.keyword_entries = self._merge_keyword_entries(domain_kw_lists)
        return merged

    def _create_directory_nodes(self, parent: ET.Element, structure: Dict[str, Any],
                              file_index: Dict[str, List[HierarchicalNode]],
                              card_groups=None, dir_annotations=None, current_abs_dir=None):
        """Recursively create directory and file nodes."""
        if card_groups is None:
            card_groups = {}
        if dir_annotations is None:
            dir_annotations = {}

        # Files at this level (regular non-card files)
        if '_files' in structure:
            for file_path in sorted(structure['_files']):
                if Path(file_path).resolve() == self.output_path.resolve():
                    continue
                if file_path in card_groups:
                    self._create_card_group_node(parent, file_path, card_groups[file_path])
                else:
                    self._create_file_node(parent, file_path)

        # Directory nodes
        for dir_name in sorted(structure.keys()):
            if dir_name.startswith('_'):
                continue

            dir_data = structure[dir_name]
            if not dir_data.get('_dirs') and not dir_data.get('_files'):
                continue

            dir_node = ET.SubElement(parent, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': dir_name
            })

            if current_abs_dir is not None:
                abs_dir = os.path.join(current_abs_dir, dir_name)
                self._add_details(dir_node, dir_annotations.get(abs_dir, ''))
            else:
                abs_dir = None

            if '_dirs' in dir_data:
                self._create_directory_nodes(dir_node, dir_data['_dirs'],
                                             file_index, card_groups,
                                             dir_annotations=dir_annotations,
                                             current_abs_dir=abs_dir)
            if '_files' in dir_data:
                for file_path in sorted(dir_data['_files']):
                    if Path(file_path).resolve() == self.output_path.resolve():
                        continue
                    if file_path in card_groups:
                        self._create_card_group_node(dir_node, file_path,
                                                     card_groups[file_path])
                    else:
                        self._create_file_node(dir_node, file_path)
    
    def _create_file_node(self, parent: ET.Element, file_path: str):
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
        
        # R-FS-002: File System Index only requires hyperlink to file, not file contents

    @staticmethod
    def _add_details(node_elem: ET.Element, text: str) -> None:
        """Attach a collapsed DETAILS panel to a Freeplane node."""
        if not text:
            return
        rc = ET.SubElement(node_elem, 'richcontent', {'TYPE': 'DETAILS', 'HIDDEN': 'true'})
        html = ET.SubElement(rc, 'html')
        ET.SubElement(html, 'head')
        body = ET.SubElement(html, 'body')
        p = ET.SubElement(body, 'p')
        p.text = text

    def _add_card_source_link(self, card_node: ET.Element, card_path: str) -> None:
        """Add a single child to a card file node linking to its original source file."""
        source_path = getattr(self, '_card_source_map', {}).get(card_path)
        if not source_path:
            return
        try:
            link_path = str(Path(source_path).relative_to(Path.cwd()))
        except ValueError:
            link_path = source_path
        ET.SubElement(card_node, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': self._display_path(source_path),
            'LINK': link_path
        })

    def _create_card_group_node(self, parent: ET.Element, source_path: str, group):
        """Create a source-file node annotated with essence + child card leaves (D21)."""
        try:
            link_path = str(Path(source_path).relative_to(Path.cwd()))
        except ValueError:
            link_path = source_path

        source_node = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': Path(source_path).name,
            'LINK': link_path,
        })
        self._add_details(source_node, group.annotation)

        for card_label, card_path, card_essence in sorted(group.cards, key=lambda x: x[0].lower()):
            if card_path == group.hidden_card:
                continue
            try:
                card_link = str(Path(card_path).relative_to(Path.cwd()))
            except ValueError:
                card_link = card_path
            card_node = ET.SubElement(source_node, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': card_label,
                'LINK': card_link,
            })
            self._add_details(card_node, card_essence)

    def _create_hierarchical_node(self, parent: ET.Element, node: HierarchicalNode,
                                base_file_path: str):
        """Create XML node from HierarchicalNode."""
        # Determine link
        link = base_file_path
        if hasattr(node, 'id') and node.id:
            # Handle markdown files specially
            if base_file_path.endswith(('.md', '.markdown')):
                # For markdown files, find the nearest heading ancestor to generate anchor
                anchor = self._find_markdown_anchor_for_node(node)
                if anchor:
                    link += f"#{anchor}"
            else:
                # For other file types (like Freeplane), use the node ID
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
    
    def _group_children_by_letter(self, parent: ET.Element, threshold: int = 20) -> None:
        """If parent has more than threshold children, re-parent them into per-letter buckets."""
        children = list(parent)
        if len(children) <= threshold:
            return

        buckets: Dict[str, list] = {}
        for child in children:
            text = child.get('TEXT', '')
            letter = text[0].upper() if text else '#'
            if not letter.isalpha():
                letter = '#'
            buckets.setdefault(letter, []).append(child)

        for child in children:
            parent.remove(child)

        for letter in sorted(buckets.keys()):
            bucket_node = ET.SubElement(parent, 'node', {
                'ID': self._generate_unique_id(),
                'CREATED': get_current_timestamp(),
                'MODIFIED': get_current_timestamp(),
                'TEXT': letter
            })
            for child in buckets[letter]:
                bucket_node.append(child)

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

        self._group_children_by_letter(kw_root)
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
                'TEXT': self._display_path(file_path),
                'LINK': link_path
            })
            self._add_details(file_node, self._card_essence_map.get(file_path, ''))

            # Add individual matches
            is_card = file_path.endswith('.kb.md')
            if is_card:
                self._add_card_source_link(file_node, file_path)
            elif link_path.endswith(('.md', '.markdown')):
                # For non-card markdown: one node per unique heading section
                seen_anchors = {}  # anchor -> (heading_text, full_link)
                no_heading = []
                for result in results:
                    if not (hasattr(result.node, 'id') and result.node.id):
                        continue
                    h = self._find_markdown_heading_node(result.node)
                    if h:
                        anchor = self._generate_markdown_anchor(h.text or '')
                        if anchor not in seen_anchors:
                            seen_anchors[anchor] = (h.text or anchor, f"{link_path}#{anchor}")
                    else:
                        no_heading.append(result)
                for _anchor, (text, link) in seen_anchors.items():
                    ET.SubElement(file_node, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': text,
                        'LINK': link
                    })
                for result in no_heading:
                    match_text = result.node.text or result.matched_content[:100]
                    if len(match_text) > 100:
                        match_text = match_text[:100] + "..."
                    ET.SubElement(file_node, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': match_text,
                        'LINK': link_path
                    })
            else:
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
                    'TEXT': self._display_path(file_path),
                    'LINK': link_path
                })
                self._add_details(file_node, self._card_essence_map.get(file_path, ''))

                if file_path.endswith('.kb.md'):
                    self._add_card_source_link(file_node, file_path)
                else:
                    # Sort individual node matches alphabetically within each file (R-TAG-008)
                    sorted_matches = sorted(file_groups[file_path], key=lambda x: x[1].lower())
                    # Create fragment hyperlinks to individual nodes (R-TAG-011).
                    # Skip matches with no node_id — those are file-level tags (e.g. markdown
                    # frontmatter) where the file_node above is already the correct link.
                    for node_id, node_text in sorted_matches:
                        if not node_id:
                            continue
                        ET.SubElement(file_node, 'node', {
                            'ID': self._generate_unique_id(),
                            'CREATED': get_current_timestamp(),
                            'MODIFIED': get_current_timestamp(),
                            'TEXT': node_text,
                            'LINK': f"{link_path}#{node_id}"
                        })

        self._group_children_by_letter(tag_root)
        return tag_root

    def _create_word_index(self, parent: ET.Element, 
                          word_results: Dict[str, Dict]) -> ET.Element:
        """Create word-based navigation index (R-WORD-001 to R-WORD-015)."""
        word_root = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': 'Word Index'
        })
        
        # Create hierarchical groupings with maximum 24 children per node (R-WORD-006)
        word_filter = SignificantWordFilter()
        sorted_words = sorted(word_results.keys(), key=str.lower)
        
        # Create hierarchical groups
        word_groups = word_filter.create_hierarchical_groups(sorted_words, max_children=24)
        
        # Build the hierarchical structure
        self._build_word_group_nodes(word_root, word_groups, word_results)
        
        return word_root
    
    def _build_word_group_nodes(self, parent: ET.Element, groups: Dict, word_results: Dict[str, Dict]):
        """Recursively build word group nodes."""
        for group_name, group_content in groups.items():
            if isinstance(group_content, dict) and 'words' in group_content:
                # This is a leaf group containing words
                if len(group_content['words']) == 1:
                    # Single word - create word node directly under parent
                    word = group_content['words'][0]
                    self._create_word_node(parent, word, word_results[word])
                else:
                    # Multiple words - create group node
                    group_node = ET.SubElement(parent, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': group_name
                    })
                    
                    # Add individual word nodes
                    for word in sorted(group_content['words'], key=str.lower):
                        self._create_word_node(group_node, word, word_results[word])
            elif isinstance(group_content, list):
                # Direct list of words (when group_name is 'words')
                if group_name == 'words':
                    # This is the base case - create word nodes directly
                    for word in sorted(group_content, key=str.lower):
                        self._create_word_node(parent, word, word_results[word])
                else:
                    # Shouldn't happen, but handle gracefully
                    group_node = ET.SubElement(parent, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': group_name
                    })
                    for word in sorted(group_content, key=str.lower):
                        self._create_word_node(group_node, word, word_results[word])
            else:
                # This is an intermediate group with subgroups (dictionary)
                group_node = ET.SubElement(parent, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': group_name
                })
                
                # Recursively process subgroups
                self._build_word_group_nodes(group_node, group_content, word_results)
    
    def _create_word_node(self, parent: ET.Element, word: str, file_matches):
        """Create node for a single word with file and match children (R-WORD-012, R-WORD-013)."""
        word_node = ET.SubElement(parent, 'node', {
            'ID': self._generate_unique_id(),
            'CREATED': get_current_timestamp(),
            'MODIFIED': get_current_timestamp(),
            'TEXT': word
        })
        
        # Handle both test format (list of files) and production format (dict of files->matches)
        if isinstance(file_matches, list):
            # Test format: simple list of file paths
            for file_path in sorted(file_matches, key=lambda x: Path(x).name.lower()):
                # Generate relative path for portability
                try:
                    rel_path = Path(file_path).relative_to(Path.cwd())
                except ValueError:
                    rel_path = Path(file_path)

                # Create simple file node without match instances
                file_node = ET.SubElement(word_node, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': self._display_path(file_path),
                    'LINK': str(rel_path)
                })
                self._add_details(file_node, self._card_essence_map.get(file_path, ''))
        else:
            # Production format: dictionary of file_path -> match_instances
            for file_path in sorted(file_matches.keys(), key=lambda x: Path(x).name.lower()):
                match_instances = file_matches[file_path]

                # Generate relative path for portability
                try:
                    rel_path = Path(file_path).relative_to(Path.cwd())
                except ValueError:
                    # Fallback if path is not relative to current directory
                    rel_path = Path(file_path)

                # Create file node (R-WORD-012)
                file_node = ET.SubElement(word_node, 'node', {
                    'ID': self._generate_unique_id(),
                    'CREATED': get_current_timestamp(),
                    'MODIFIED': get_current_timestamp(),
                    'TEXT': self._display_path(file_path),
                    'LINK': str(rel_path)
                })
                self._add_details(file_node, self._card_essence_map.get(file_path, ''))

                if file_path.endswith('.kb.md'):
                    self._add_card_source_link(file_node, file_path)
                    continue

                # Create match instance nodes as children of file node (R-WORD-013)
                for match_instance in match_instances:
                    node_text = match_instance.get('node_text', 'Content')
                    node_id = match_instance.get('node_id', '')
                    node_type = match_instance.get('node_type', 'content')
                    
                    # Generate appropriate link with fragment
                    if node_id:
                        # For freeplane files, use node ID
                        if file_path.endswith('.mm'):
                            link_fragment = f"{rel_path}#{node_id}"
                        # For markdown files, try to generate GitHub-style anchor
                        elif file_path.endswith(('.md', '.markdown')):
                            if node_type == 'heading' and node_text:
                                anchor = self._generate_markdown_anchor(node_text)
                                link_fragment = f"{rel_path}#{anchor}" if anchor else str(rel_path)
                            else:
                                link_fragment = str(rel_path)  # No fragment for non-heading nodes
                        else:
                            link_fragment = str(rel_path)
                    else:
                        link_fragment = str(rel_path)
                    
                    # Create match instance node
                    match_node = ET.SubElement(file_node, 'node', {
                        'ID': self._generate_unique_id(),
                        'CREATED': get_current_timestamp(),
                        'MODIFIED': get_current_timestamp(),
                        'TEXT': node_text if node_text else 'Content',
                        'LINK': link_fragment
                    })
    
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

        # Stamp the provenance marker as a comment just inside <map> (where
        # Freeplane writes its own comment), so a later kbi run skips this file.
        from index_model import marker_comment
        if lines and lines[0].lstrip().startswith('<map'):
            lines.insert(1, '  ' + marker_comment())

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