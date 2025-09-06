#!/usr/bin/env python3
"""Keyword file parsing and processing."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KeywordEntry:
    """Represents a keyword entry in the hierarchy."""
    text: str
    level: int
    is_leaf: bool  # True if this is a search pattern, False if organizational
    children: List['KeywordEntry'] = None
    parent: Optional['KeywordEntry'] = None
    line_number: int = 0
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def add_child(self, child: 'KeywordEntry'):
        """Add a child entry."""
        child.parent = self
        self.children.append(child)
    
    def get_search_sequences(self) -> List[List[str]]:
        """Get all search sequences from this entry and its descendants."""
        sequences = []
        
        if self.is_leaf:
            # This is a search pattern
            if ':' in self.text:
                # Multi-term sequence
                terms = [term.strip() for term in self.text.split(':')]
                sequences.append(terms)
            else:
                # Single term
                sequences.append([self.text])
        else:
            # This is organizational - get sequences from children
            for child in self.children:
                child_sequences = child.get_search_sequences()
                sequences.extend(child_sequences)
        
        return sequences
    
    def get_display_name(self) -> str:
        """Get display name for this entry."""
        if ':' in self.text:
            return self.text.replace(':', ' → ')
        return self.text


class KeywordFileParser:
    """Parser for tab-indented keyword files."""
    
    def __init__(self, tab_size: int = 1):
        """Initialize parser with tab configuration."""
        self.tab_size = tab_size
    
    def parse_file(self, file_path: str) -> List[KeywordEntry]:
        """Parse a keyword file and return root entries."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Keyword file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        return self.parse_lines(lines)
    
    def parse_lines(self, lines: List[str]) -> List[KeywordEntry]:
        """Parse lines into keyword entries."""
        entries = []
        entry_stack = []  # Stack to track parent entries
        
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines
            stripped = line.rstrip()
            if not stripped:
                continue
            
            # Calculate indentation level
            level = self._calculate_indentation_level(line)
            content = stripped.lstrip('\t ')
            
            # Skip comments and empty content after stripping indentation
            if not content or content.startswith('#'):
                continue
            
            # Pop entries from stack until we find the correct parent level
            while entry_stack and entry_stack[-1].level >= level:
                entry_stack.pop()
            
            # Determine if this is a leaf entry (will be determined after parsing all children)
            entry = KeywordEntry(
                text=content,
                level=level,
                is_leaf=True,  # Will be updated if children are found
                line_number=line_num
            )
            
            # Add to parent or root
            if entry_stack:
                entry_stack[-1].add_child(entry)
                entry_stack[-1].is_leaf = False  # Parent is not a leaf
            else:
                entries.append(entry)
            
            entry_stack.append(entry)
        
        return entries
    
    def _calculate_indentation_level(self, line: str) -> int:
        """Calculate indentation level based on tabs."""
        level = 0
        for char in line:
            if char == '\t':
                level += 1
            elif char == ' ':
                # Count spaces as partial tabs (assuming 4 spaces = 1 tab)
                level += 0.25
            else:
                break
        return int(level)
    
    def validate_structure(self, entries: List[KeywordEntry]) -> List[str]:
        """Validate keyword file structure and return any warnings."""
        warnings = []
        
        def validate_entry(entry: KeywordEntry, path: List[str] = None) -> None:
            if path is None:
                path = []
            
            current_path = path + [entry.text]
            
            # Check for empty content
            if not entry.text.strip():
                warnings.append(f"Empty entry at line {entry.line_number}")
            
            # Check for invalid colon usage in non-leaf entries
            if not entry.is_leaf and ':' in entry.text:
                warnings.append(f"Non-leaf entry contains colon at line {entry.line_number}: {entry.text}")
            
            # Check for very deep nesting (warn only once per branch when threshold exceeded)
            if len(current_path) == 7:  # Exactly 7 levels deep
                warnings.append(f"Very deep nesting (level {len(current_path)}) at line {entry.line_number}")
            
            # Validate children
            for child in entry.children:
                validate_entry(child, current_path)
        
        for entry in entries:
            validate_entry(entry)
        
        return warnings


class KeywordProcessor:
    """Processes keyword entries for search operations."""
    
    def __init__(self):
        self.debug = False
    
    def set_debug(self, debug: bool):
        """Enable or disable debug output."""
        self.debug = debug
    
    def extract_all_search_sequences(self, entries: List[KeywordEntry]) -> Dict[str, List[List[str]]]:
        """Extract all search sequences organized by category."""
        sequences_by_category = {}
        
        # Process top-level entries
        for entry in entries:
            if entry.is_leaf:
                # This is a leaf node - add its search patterns to a "Direct Searches" category
                sequences = entry.get_search_sequences()
                if sequences:
                    if "Direct Searches" not in sequences_by_category:
                        sequences_by_category["Direct Searches"] = []
                    sequences_by_category["Direct Searches"].extend(sequences)
                    
                    if self.debug:
                        print(f"Direct search '{entry.text}': {len(sequences)} sequences")
                        for seq in sequences:
                            print(f"  {' → '.join(seq)}")
            else:
                # This is an interior node - treat as category containing children's search patterns
                category_name = entry.text
                sequences = entry.get_search_sequences()
                
                if sequences:
                    sequences_by_category[category_name] = sequences
                    
                    if self.debug:
                        print(f"Category '{category_name}': {len(sequences)} sequences")
                        for seq in sequences:
                            print(f"  {' → '.join(seq)}")
        
        return sequences_by_category
    
    def flatten_search_sequences(self, entries: List[KeywordEntry]) -> List[List[str]]:
        """Get all search sequences as a flat list."""
        all_sequences = []
        
        for entry in entries:
            sequences = entry.get_search_sequences()
            all_sequences.extend(sequences)
        
        return all_sequences
    
    def build_organizational_hierarchy(self, entries: List[KeywordEntry]) -> Dict[str, Any]:
        """Build hierarchical structure for display purposes."""
        hierarchy = {}
        
        for entry in entries:
            hierarchy[entry.text] = self._build_entry_hierarchy(entry)
        
        return hierarchy
    
    def _build_entry_hierarchy(self, entry: KeywordEntry) -> Dict[str, Any]:
        """Build hierarchy for a single entry."""
        result = {
            'text': entry.text,
            'display_name': entry.get_display_name(),
            'is_leaf': entry.is_leaf,
            'level': entry.level,
            'children': {}
        }
        
        if entry.is_leaf:
            if ':' in entry.text:
                result['search_sequence'] = [term.strip() for term in entry.text.split(':')]
            else:
                result['search_sequence'] = [entry.text]
        
        for child in entry.children:
            result['children'][child.text] = self._build_entry_hierarchy(child)
        
        return result


def load_keyword_files(keyword_files: List[str], debug: bool = False) -> Tuple[List[KeywordEntry], List[str]]:
    """
    Load and parse multiple keyword files.
    
    Args:
        keyword_files: List of keyword file paths
        debug: Enable debug output
    
    Returns:
        Tuple of (all entries, warnings)
    """
    parser = KeywordFileParser()
    all_entries = []
    all_warnings = []
    
    for file_path in keyword_files:
        try:
            if debug:
                print(f"Loading keyword file: {file_path}")
            
            entries = parser.parse_file(file_path)
            warnings = parser.validate_structure(entries)
            
            all_entries.extend(entries)
            all_warnings.extend([f"{file_path}: {w}" for w in warnings])
            
            if debug:
                print(f"  Loaded {len(entries)} root entries")
                if warnings:
                    print(f"  Warnings: {warnings}")
        
        except Exception as e:
            warning = f"Error loading {file_path}: {e}"
            all_warnings.append(warning)
            if debug:
                print(f"  {warning}")
    
    return all_entries, all_warnings


def create_sample_keyword_file(output_path: str):
    """Create a sample keyword file for reference."""
    sample_content = """# Sample keyword file
# Lines starting with # are comments
# Use tabs for indentation
# Leaf entries (no children) are search patterns
# Non-leaf entries are organizational categories

Programming Concepts
	Functions
		function:definition
		async:function
		lambda:function
	Classes
		class:inheritance
		abstract:class
		interface:implementation
	Error Handling
		try:catch:exception
		error:handling:best:practices

Documentation
	API Documentation
		api:reference
		endpoint:documentation
	User Guides
		tutorial:beginner
		guide:advanced:usage

Project Management
	Planning
		requirements:analysis
		project:scope
	Development Process
		code:review:process
		testing:strategy
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print(f"Sample keyword file created: {output_path}")