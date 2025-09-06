# Knowledgebase Indexer

A Python implementation of the Knowledgebase Indexer that creates navigational mind map indexes for collections of structured files, as specified in `mmdir_PRD.md`.

## Features

- **File System Index**: Hierarchical directory view mirroring physical structure
- **Keyword Index**: Context-sensitive search with hierarchical scope narrowing
- **Tag Index**: Tag-based file organization
- **Extensible Architecture**: Plugin-based file handlers
- **Freeplane Compatibility**: Generates valid Freeplane .mm files

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make the script executable:
```bash
chmod +x mmdir.py
```

## Usage

### Basic Usage

```bash
# Generate index with default settings
python3 kbi.py

# Enable debug output
python3 kbi.py --debug

# Use specific configuration file
python3 kbi.py --config myconfig.yml

# Specify output file
python3 kbi.py --output my_index.mm
```

### Sample Files

Generate sample configuration and keyword files:

```bash
# Create sample configuration
python3 kbi.py --sample-config

# Create sample keyword file
python3 kbi.py --sample-keywords
```

## Configuration

The application uses YAML configuration files. Default locations searched:
1. Command line `--config` argument
2. `./config/kbi.yml` or `./config/kbi.yaml`
3. `./kbi.yml` or `./kbi.yaml`
4. `~/.config/kbi/config.yml`

### Configuration Structure

```yaml
directories:
  include:
    - "**/*.mm"
    - "**/*.md"
  exclude:
    - "**/node_modules/**"
    - "**/.git/**"

keywords:
  files:
    - "keywords.txt"

output:
  file: "index.mm"
  format: "freeplane"

file_types:
  freeplane:
    extensions: [".mm"]
    handler: "FreeplaneHandler"
  markdown:
    extensions: [".md", ".markdown"] 
    handler: "MarkdownHandler"
```

## Keyword Files

Keyword files use tab-indented structure with hierarchical context-sensitive search:

```
Programming Concepts
	Functions
		function:definition
		async:function
	Classes
		class:inheritance
		interface:implementation
	Error Handling
		try:catch:exception
```

With the indention forming a hierarchy of interior nodes and leaf nodes:

- only leaf nodes are keyword search patterns, all interior nodes are for grouping keyword search patterns
- ':' separates keywords to form a keyword sequence search (hierarchical contextual search)
- `#` lines are comments

The keyword search patterns are regular expressions.

The keyword file is used to form the 'keyword index' branch in the results.  On that branch should be the terms in the keyword file in the same hierarchical organization (including leaf nodes).  The leaf nodes (the keyword search patterns) will then have the search results of that pattern as children nodes of it.  (And no children if there are no matches of that keyword search pattern.)

The terms in the keyword index branch should be in alphabetical order at each level.

## Supported File Types

- **Freeplane (.mm)**: XML-based mind maps with node hierarchy
- **Markdown (.md, .markdown)**: Composite hierarchy (headers + lists)

## Architecture

The implementation follows the PRD's modular architecture:

- `config.py`: Configuration loading and validation
- `handlers/`: File type handlers with plugin architecture
- `search.py`: Hierarchical context-sensitive search engine
- `keywords.py`: Keyword file parsing and processing
- `mindmap_generator.py`: Freeplane XML generation
- `kbi.py`: Main application entry point

## Output

Generates Freeplane-compatible .mm files with three main branches:

1. **File System Index**: Directory structure with file hierarchy
2. **Keyword Index**: Search results organized by keyword sequences
3. **Tag Index**: Files grouped by extracted tags

## Examples

Process markdown and mind map files in current directory:
```bash
python3 kbi.py --debug
```

Generate index with custom keyword searches:
```bash
echo -e "Documentation\n\tAPI\n\t\tapi:reference\n\tGuides\n\t\ttutorial:beginner" > keywords.txt
python3 kbi.py --debug
```
