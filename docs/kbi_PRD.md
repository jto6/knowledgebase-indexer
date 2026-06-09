# Product Requirements Document: Knowledgebase Indexer (KBI)

## PART I: REQUIREMENTS

## 1. Overview

The Knowledgebase Indexer builds navigational indexes over collections of
structured files. Its core output is a **render-independent index model** — four
navigation views (File System, Keyword, Tag, Word) computed from files matching
configurable patterns. That model is then emitted by one or more **renderers**.

The requirements in this document describe the index model in render-neutral
terms: a *node* is a model element, a *branch* is a view, and a *link* is a
reference from one element to a file (or to a location within a file). Each
renderer materializes those concepts in its own form.

### 1.1 Renderers

- **Freeplane `.mm`** — the reference renderer (a navigable mind map). Renderer-
  specific requirements live in §2.5 and in Part II §4. This is the only renderer
  the original implementation targeted, and the default today.
- **Markdown** — a Claude-facing renderer producing a per-domain navigational
  index (`INDEX.md` + `<domain>.md` files) of key→file-location links.

Both renderers serialize one shared model, partitioned by domain, whose views
include the four below plus the card-only Dependencies and Glossary views; view
emission is configurable (`output.views`). `output.format` selects only the
serialization. See `DESIGN_PRINCIPLES_AND_DECISIONS.md` (D16) for the model,
domain partitioning, and per-view emission, which supersede the format-specific
phrasing in the requirements below.

## 2. Functional Requirements

### 2.1 File System Index
- **R-FS-001**: Generate hierarchical directory view of searched files, mirroring physical directory structure
- **R-FS-002**: For each searched file, include a hyperlink to it as a child node of the node of the directory it is in
- **R-FS-003**: Exclude directories containing no indexed files from the navigation tree
- **R-FS-004**: Only include indexed files from each directory
- **R-FS-005**: Exclude the generated index file from its own navigation
- **R-FS-006**: Sort directories before files, both alphabetically (case-insensitive)  
  **R-FS-008**: File System branch in output file should not include the directory path common to all directories that were searched (eg, if search directories are A/B/C/D and A/B/E, then output directory structure should exclude A/B and only show paths C/D and E)

### 2.2 Keyword Index
- **R-KW-001**: Display keyword hierarchy as parent / child nodes in the output mind map
- **R-KW-012**: Sort keyword terms alphabetically at each hierarchy level (case-insensitive)
- **R-KW-013**: Display leaf nodes with their search results as child nodes for each matched file, when matches are found
- **R-KW-014**: Display leaf nodes with no child nodes when no matches are found for that pattern
- **R-KW-015**: Group all matches from same file under the file's node
- **R-KW-016**: Each match under the file's node is a hyperlink to individual nodes using `filepath#nodeId` format

### 2.3 Tag Index
- **R-TAG-001**: Extract tags from searched files using each file type's specific tag encoding scheme
- **R-TAG-002**: Include tag index only when tags are found in any of the searched file collection
- **R-TAG-003**: Create three-level hierarchy: Tag → File → Individual Node Match
- **R-TAG-004**: Group all matches for same tag-file combination under single file node
- **R-TAG-005**: Sort tags alphabetically at top level (case-insensitive)
- **R-TAG-006**: Sort files alphabetically within each tag group (case-insensitive by filename)
- **R-TAG-007**: Sort individual node matches alphabetically within each file (case-insensitive by node text)
- **R-TAG-008**: Create hyperlinks to files at file level using relative paths
- **R-TAG-009**: Create fragment hyperlinks to individual sections of the file for section-local tags

### 2.4 Word Index
- **R-WORD-001**: Generate Word Index as fourth main branch of mind map output
- **R-WORD-002**: Extract significant words from all processed file content using technical word filtering
- **R-WORD-003**: Exclude common stop words, pronouns, conjunctions, prepositions, and non-specific terms
- **R-WORD-004**: Include technical terms, proper nouns, compound words, and domain-specific vocabulary
- **R-WORD-005**: Apply minimum frequency threshold (default 2 occurrences) for word inclusion
- **R-WORD-006**: Create hierarchical word groupings with maximum 24 children per node at any level
- **R-WORD-007**: Group words alphabetically by first character when feasible
- **R-WORD-008**: Create character range nodes (e.g., "d-f", "at-aw") when single characters exceed 24 words
- **R-WORD-009**: Subdivide large groups by 2-3 character prefixes maintaining 24-child limit
- **R-WORD-010**: Keep hierarchy as flat as possible while respecting node count constraints
- **R-WORD-011**: Each word node should have children representing files containing that word
- **R-WORD-012**: File nodes should have children for each specific match instance within that file
- **R-WORD-013**: Match instance links should point to specific elements (markdown headers, freeplane nodes)
- **R-WORD-014**: Consolidate word variations using regex patterns when combined matches are fewer than 24
- **R-WORD-015**: Common variations include plurals (sdk/sdks → sdks?), verb forms (process/processing → process.*), and technical suffixes
- **R-WORD-016**: Eliminate redundant single-character grouping in hierarchical organization
- **R-WORD-017**: Apply word boundary matching for accurate word extraction
- **R-WORD-018**: Filter out pure numbers and predominantly numeric strings
- **R-WORD-019**: Preserve technical abbreviations and acronyms (API, HTTP, CPU, etc.)

### 2.5 Output Generation (Freeplane `.mm` renderer)

These requirements are specific to the reference Freeplane renderer; other
renderers (e.g. the planned Markdown renderer) satisfy their own equivalents.

- **R-OUT-001**: Generate valid Freeplane-compatible .mm XML files
- **R-OUT-002**: Use human-readable pretty-printed XML formatting
- **R-OUT-003**: Assign unique node IDs across entire output file
- **R-OUT-004**: Include creation and modification timestamps for all nodes
- **R-OUT-005**: Use relative paths for all file links to ensure portability

## 3. Configuration Requirements

### 3.1 YAML Configuration File
- **R-CFG-001**: Define all operational parameters in YAML configuration file
- **R-CFG-002**: Validate configuration against JSON schema
- **R-CFG-003**: Support configuration file discovery in standard locations

### 3.2 Directory Selection Configuration
- **R-CFG-004**: Specify directories to search using glob pattern syntax
- **R-CFG-005**: Specify directories to exclude using glob pattern syntax  
- **R-CFG-006**: Support multiple include and exclude patterns

### 3.3 File Type Configuration
- **R-CFG-007**: Define supported file types via extensible YAML configuration
- **R-CFG-008**: Map file extensions to handler implementations
- **R-CFG-009**: Configure file-type-specific search and link behaviors
- **R-CFG-010**: Define hierarchical structure interpretation for each file type

### 3.4 Keyword Configuration
- **R-CFG-011**: Specify keyword file location in configuration
- **R-CFG-012**: Support multiple keyword files
- **R-CFG-013**: Configure keyword file format parameters

### 3.5 Output Configuration
- **R-CFG-014**: Specify output file location in configuration
- **R-CFG-015**: Configure output format parameters

## 4. Interface Requirements

### 4.1 Configuration File Schema
```yaml
# Main configuration structure
directories:
  include: [<glob_patterns>]
  exclude: [<glob_patterns>]

keywords:
  files: [<file_paths>]
  
output:
  file: <output_path>
  format: <output_format>
  
file_types:
  <type_name>:
    extensions: [<extensions>]
    handler: <handler_class>
    hierarchy_config: <hierarchy_definition>
    search_config: <search_parameters>
    link_config: <link_parameters>
```

### 4.2 File Type Hierarchy Configuration
- **R-HIER-001**: Define hierarchical structure interpretation for each file type
- **R-HIER-002**: Specify parent-child relationships in structured content
- **R-HIER-003**: Support different hierarchy models (node-based, heading-based, list-based)
- **R-HIER-004**: For heading-based hierarchies: include heading text and content until next same-or-higher level heading in the node
- **R-HIER-005**: Support combined hierarchy models (both headings and lists within same file)

```yaml
# Example hierarchy configurations
file_types:
  freeplane:
    hierarchy_config:
      type: "xml_nodes"
      parent_element: "node"
      child_selector: "./node"
      
  markdown:
    hierarchy_config:
      type: "composite"
      structures:
        - type: "heading_levels"
          heading_tags: ["h1", "h2", "h3", "h4", "h5", "h6"]
          content_scope: "heading_plus_content_until_next_heading"
        - type: "nested_lists"
          list_types: ["ul", "ol"]
          nesting_logic: "indentation_based"
      
  structured_text:
    hierarchy_config:
      type: "indented_lists"
      indent_char: " "
      indent_size: 2
```

### 4.3 Keyword File Syntax
- **R-KW-SYNTAX-001**: Use tab characters for indentation levels to form hierarchy of interior and leaf nodes
- **R-KW-SYNTAX-002**: Each line represents either organizational group or search pattern
- **R-KW-SYNTAX-003**: Lines with child lines (based on indentation) are interior nodes for organizational grouping only
- **R-KW-SYNTAX-004**: Lines without child lines are leaf nodes containing search patterns (regular expressions)
- **R-KW-SYNTAX-005**: Use colon (`:`) to separate hierarchical context-sensitive search terms in leaf nodes (see section 4.4 for hierarchical search semantics)
- **R-KW-SYNTAX-006**: Support comment lines beginning with `#`
- **R-KW-SYNTAX-007**: Apply word boundary regex matching to each search term
- **R-KW-SYNTAX-008**: Ignore empty lines and whitespace-only lines
- **R-KW-SYNTAX-009**: Treat keyword search patterns as regular expressions with word boundary constraints

### 4.4 Hierarchical Context-Sensitive Search Semantics
- **R-SEARCH-001**: Execute hierarchical context-sensitive search as a sequence of search terms
- **R-SEARCH-002**: First term searches entire file content using file type's hierarchy definition
- **R-SEARCH-003**: Each subsequent search term searches within nodes and their descendants from previous matches
- **R-SEARCH-004**: Non-final search terms do not search a matching node's descendants (early termination for context preservation)
- **R-SEARCH-005**: Final search term finds all matches within the constrained scope (no early termination)
- **R-SEARCH-006**: Preserve hierarchical context throughout search sequence

### 4.5 File Handler Interface
- **R-HDL-001**: Implement standardized handler interface for file type processing
- **R-HDL-002**: Support content extraction for search operations
- **R-HDL-003**: Support hierarchical navigation according to file type's hierarchy definition
- **R-HDL-004**: Support tag extraction for tag index generation
- **R-HDL-005**: Generate appropriate link formats for file type
- **R-HDL-006**: Validate file compatibility before processing

### 4.6 Freeplane Tag Processing Requirements
- **R-FREEPLANE-TAG-001**: Extract tags from Freeplane node `TAGS` attributes
- **R-FREEPLANE-TAG-002**: Handle HTML entities and encoded characters in tag attribute values  
- **R-FREEPLANE-TAG-003**: Replace encoded newlines (`&#xa;`) with spaces in tag values
- **R-FREEPLANE-TAG-004**: Split tag attribute values on whitespace to extract individual tags
- **R-FREEPLANE-TAG-005**: Associate extracted tags with node ID and node text for linking

### 4.7 Markdown Tag Processing Requirements
- **R-MARKDOWN-TAG-001**: Extract hashtag-style tags using pattern `#tagname` from markdown content
- **R-MARKDOWN-TAG-002**: Extract tags from YAML frontmatter `tags:` or `tag:` fields
- **R-MARKDOWN-TAG-003**: Support YAML list format: `tags: [tag1, tag2, tag3]`
- **R-MARKDOWN-TAG-004**: Support comma-separated format: `tags: tag1, tag2, tag3`
- **R-MARKDOWN-TAG-005**: Strip quotes and whitespace from YAML tag values
- **R-MARKDOWN-TAG-006**: Combine hashtag and frontmatter tags into unified tag list
- **R-MARKDOWN-TAG-007**: Associate tags with file-level context for linking

## 5. Quality Requirements

### 5.1 Extensibility
- **R-EXT-001**: Add new file types without modifying core code
- **R-EXT-002**: Support pluggable handler architecture
- **R-EXT-003**: Configure new hierarchy types without code changes
- **R-EXT-004**: Maintain backward compatibility for existing functionality

### 5.2 Reliability  
- **R-REL-001**: Continue processing when individual files fail
- **R-REL-002**: Provide meaningful error messages for configuration issues
- **R-REL-003**: Validate all configuration before processing begins

### 5.3 Performance
- **R-PERF-001**: Process large directory structures efficiently
- **R-PERF-002**: Minimize memory usage during file processing
- **R-PERF-003**: Support caching for improved performance on repeated operations

---

## PART II: INFORMATIVE

## 1. Implementation Architecture

### 1.1 Processing Pipeline
The system follows a multi-stage pipeline:

1. Configuration loading and validation
2. Directory scanning and file discovery  
3. File type detection and handler selection
4. Content extraction and hierarchical indexing
5. Hierarchical context-sensitive search execution
6. Result aggregation and grouping
7. Rendering and output formatting (Freeplane `.mm` by default)

### 1.2 Key Design Patterns

**Plugin Architecture**: File type handlers implement a common interface, enabling extensibility without core modifications.

**Configuration-Driven Behavior**: All operational parameters externalized to YAML configuration, reducing hard-coded dependencies.

**Hierarchical Processing**: Keyword processing uses tree structures to separate organizational hierarchy from search semantics.

**Context-Preserving Search**: Sequential search terms maintain hierarchical scope through the search process.

## 2. Hierarchical Context-Sensitive Search Algorithm

### 2.1 Search Sequence Processing
The algorithm implements a sophisticated hierarchical scope-narrowing process:

1. **Initial Scope**: First term searches entire file content within the file's hierarchical structure
2. **Scope Narrowing**: Each subsequent term searches within the matched node and all its hierarchical descendants from previous matches
3. **Context Preservation**: The hierarchical relationship between parent and child content is maintained throughout the sequence
4. **Result Scoping**: Final results are constrained to the narrowest hierarchical context established by the search sequence

### 2.2 Early Termination Strategy
For non-final terms in a search sequence:

- **Subtree Matching**: When searching within a node's subtree, return the first match found
- **Match Priority**: If the parent node itself matches, return it; otherwise return the first matching descendant
- **Traversal Termination**: Stop searching the subtree after finding the first match to preserve the specific hierarchical context

This ensures that subsequent search terms operate within a specific hierarchical context rather than all possible matches.

### 2.3 Final Term Collection
For the final term in a search sequence:

- **Complete Collection**: Return all matches within the established hierarchical scope
- **Exhaustive Search**: Continue searching through all nodes in the constrained subtree
- **Context Preservation**: All final matches are guaranteed to be within the hierarchical context established by previous terms

## 3. File Type Hierarchy Abstraction

### 3.1 Hierarchy Model Types

**XML Node Hierarchy** (e.g., Freeplane .mm files):

- Parent-child relationships defined by XML element nesting
- Navigation follows DOM tree structure
- Search scope constrained by XML parent-child relationships

**Heading Level Hierarchy** (e.g., Markdown files):

- Parent-child relationships defined by heading level (H1 > H2 > H3, etc.)
- Node content includes heading text plus all content until next same-or-higher level heading
- Search scope follows heading hierarchy and content sections

**Nested List Hierarchy** (e.g., Markdown lists, structured text):

- Parent-child relationships defined by list nesting or indentation levels
- Search scope follows list item hierarchy

**Composite Hierarchy** (e.g., Markdown with both headers and lists):

- Combines multiple hierarchy models within same file
- Headers create primary structure, nested lists create sub-structure within header sections

### 3.2 Markdown Hierarchy Specification

For Markdown files, the hierarchy combines two structures:

**Header-Based Hierarchy**:
```
# Main Topic (H1)
Some introductory content here.

A paragraph that belongs to Main Topic.

## Subtopic A (H2)
Content specific to Subtopic A.

### Detail 1 (H3)
Detailed information.

## Subtopic B (H2)
More content.
```

Node structure:

- "Main Topic" node contains: heading text + "Some introductory content here." + "A paragraph that belongs to Main Topic."
- "Subtopic A" node (child of Main Topic) contains: heading text + "Content specific to Subtopic A."
- "Detail 1" node (child of Subtopic A) contains: heading text + "Detailed information."
- "Subtopic B" node (child of Main Topic) contains: heading text + "More content."

**List-Based Hierarchy**:
```
- Top level item
  - Nested item 1
    - Deep nested item
  - Nested item 2
- Another top level item
```

Node structure follows indentation/nesting levels.

**Combined Hierarchy**: When both headers and lists exist, lists are treated as hierarchical structures within their containing header sections.

### 3.3 Hierarchy Configuration Schema
```yaml
hierarchy_config:
  type: <hierarchy_model>
  navigation_rules:
    parent_selector: <how_to_find_parent>
    child_selector: <how_to_find_children>
    content_scope: <what_content_belongs_to_node>
  search_behavior:
    scope_inheritance: <how_children_inherit_parent_scope>
    termination_rules: <when_to_stop_searching_subtree>
```

### 3.4 Handler Hierarchy Interface
```python
class HierarchicalHandler(FileHandler):
    def get_root_nodes(self, file_path):
        """Return top-level nodes in the file's hierarchy."""
        pass
    
    def get_child_nodes(self, parent_node):
        """Return direct children of the given node."""
        pass
    
    def get_node_content(self, node):
        """Extract searchable content from a node."""
        pass
    
    def search_in_node_subtree(self, node, pattern, include_descendants=True):
        """Search within a node and optionally its descendants."""
        pass
```

## 4. Freeplane .mm File Compliance

This section specifies the reference Freeplane renderer. Planned renderers (e.g.
the Markdown / Claude-facing renderer) have their own output specifications and
are not bound by these XML requirements.

### 4.1 Critical XML Structure
Freeplane requires specific XML structure for compatibility:

**Root Element**: Must be `<map version="freeplane 1.12.1">`

**Node Requirements**: Each node must include:

- `ID` attribute: Unique identifier (format: `ID_` + uppercase hex)
- `CREATED` and `MODIFIED` attributes: Timestamp format `YYYYMMDDTHHMMSS`  
- `TEXT` attribute: Node display text

**Link Format**: Use `LINK` attribute with relative paths. Fragment identifiers: `path/file.ext#NODE_ID`

### 4.2 Proven XML Generation Approach
Use Python's `xml.etree.ElementTree` for structure building combined with `xml.dom.minidom` for pretty-printing:

```python
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Build structure
root = Element('map', {'version': 'freeplane 1.12.1'})
node = SubElement(parent, 'node', {
    'ID': generate_id(),
    'CREATED': get_timestamp(), 
    'MODIFIED': get_timestamp(),
    'TEXT': display_text
})

# Pretty-print output
rough_xml = tostring(root, encoding='unicode', method='xml')
reparsed = minidom.parseString(rough_xml)
pretty_xml = reparsed.toprettyxml(indent="  ", newl="\n")
```

## 5. Search Implementation Details

### 5.1 Context-Sensitive Sequential Search Implementation
```python
def hierarchical_search(files, sequence, handler):
    current_matches = defaultdict(list)
    
    # First keyword: search entire files
    for file_path in files:
        root_nodes = handler.get_root_nodes(file_path)
        for root in root_nodes:
            matches = search_in_subtree(root, sequence[0], is_last=(len(sequence)==1))
            current_matches[file_path].extend(matches)
    
    # Subsequent keywords: search within previous matches and their descendants
    for i, keyword in enumerate(sequence[1:], 1):
        is_last = (i == len(sequence) - 1)
        new_matches = defaultdict(list)
        
        for file_path, nodes in current_matches.items():
            for node in nodes:
                # Search within this node AND its entire subtree
                matches = search_in_subtree(node, keyword, is_last)
                new_matches[file_path].extend(matches)
        
        current_matches = new_matches
        if not current_matches:
            break
    
    return current_matches

def search_in_subtree(node, pattern, is_last_keyword):
    matches = []
    
    # Check current node
    if pattern.search(handler.get_node_content(node)):
        matches.append(node)
        if not is_last_keyword:
            return matches  # Early termination for context preservation
    
    # Search descendants
    for child in handler.get_child_nodes(node):
        child_matches = search_in_subtree(child, pattern, is_last_keyword)
        if child_matches:
            matches.extend(child_matches)
            if not is_last_keyword:
                break  # Early termination - preserve specific hierarchical path
    
    return matches
```

### 5.2 Markdown Content Aggregation Strategy
For Markdown files with header-based hierarchy:

```python
def extract_header_section_content(self, header_node):
    """Extract header text plus content until next same-or-higher level header."""
    content_parts = [header_node.text]  # Include header text
    
    current_element = header_node.next_sibling
    header_level = self.get_header_level(header_node)
    
    while current_element:
        if self.is_header(current_element):
            if self.get_header_level(current_element) <= header_level:
                break  # Stop at same or higher level header
        content_parts.append(self.extract_text_content(current_element))
        current_element = current_element.next_sibling
    
    return ' '.join(content_parts)
```

### 5.3 Regex Pattern Construction
Use word boundary matching to prevent false positives:

```python
pattern = re.compile(rf'\b({keyword})\b', re.IGNORECASE)
```

## 6. File Type Extension Examples

### 6.1 Markdown Handler with Composite Hierarchy
```python
class MarkdownHandler(HierarchicalHandler):
    def __init__(self, config):
        self.config = config
        
    def get_root_nodes(self, file_path):
        # Parse markdown and return top-level structure
        parsed = self.parse_markdown(file_path)
        return self.build_composite_hierarchy(parsed)
    
    def build_composite_hierarchy(self, parsed_content):
        # Build hierarchy combining headers and lists
        nodes = []
        
        # First pass: create header-based hierarchy
        header_nodes = self.create_header_hierarchy(parsed_content)
        
        # Second pass: add list hierarchies within header sections
        for header_node in header_nodes:
            list_nodes = self.extract_lists_in_section(header_node)
            header_node.add_child_structures(list_nodes)
        
        return header_nodes
    
    def get_node_content(self, node):
        if node.type == 'header':
            return self.extract_header_section_content(node)
        elif node.type == 'list_item':
            return node.text
        
    def search_in_node_subtree(self, node, pattern, include_descendants=True):
        matches = []
        
        # Search node content
        if pattern.search(self.get_node_content(node)):
            matches.append(node)
            if not include_descendants:
                return matches
        
        # Search child nodes (both header children and list children)
        for child in self.get_child_nodes(node):
            child_matches = self.search_in_node_subtree(child, pattern, include_descendants)
            if child_matches:
                matches.extend(child_matches)
                if not include_descendants:
                    break
        
        return matches
```

Configuration:
```yaml
file_types:
  markdown:
    extensions: [".md", ".markdown"]
    handler: "MarkdownHandler"
    hierarchy_config:
      type: "composite"
      structures:
        - type: "heading_levels"
          heading_tags: ["h1", "h2", "h3", "h4", "h5", "h6"]
          content_scope: "heading_plus_content_until_next_heading"
        - type: "nested_lists"
          list_types: ["ul", "ol"]
          nesting_logic: "indentation_based"
    search_config:
      content_fields: ["heading_text", "section_content", "list_item_text"]
    link_config:
      format: "{path}#{anchor}"
      supports_fragments: true
```

## 7. Configuration Management

### 7.1 Schema Validation
Implement JSON Schema validation for configuration files to catch errors early:

```python
import jsonschema

def validate_config(config_data, schema_path):
    with open(schema_path) as f:
        schema = json.load(f)
    jsonschema.validate(config_data, schema)
```

### 7.2 Configuration Discovery Order
Search for configuration files in this priority order:

1. Command line `--config` argument
2. `./config/` in current working directory
3. User configuration directory (`~/.config/mmdir/`)
4. Built-in defaults

### 7.3 Handler Registration
Use dynamic loading for extensible handler architecture:

```python
import importlib

def load_handler(handler_name, config):
    module_name = f"handlers.{handler_name.lower()}"
    module = importlib.import_module(module_name)
    handler_class = getattr(module, handler_name)
    return handler_class(config)
```

## 8. Testing Considerations

### 8.1 Hierarchical Search Testing
- Test context-sensitive sequences with known hierarchical content
- Verify early termination preserves correct hierarchical context
- Test that final terms collect all matches within established scope
- Test different hierarchy types (XML, heading-based, nested lists, composite)

### 8.2 Markdown Hierarchy Testing
- Test header-based content inclusion (header + content until next header)
- Test nested list hierarchy within header sections
- Test composite hierarchy navigation
- Verify content boundaries are correctly maintained

### 8.3 Configuration Validation Testing  
- Test schema validation with invalid configurations
- Verify error messages for common hierarchy configuration mistakes
- Test configuration discovery in different environments
