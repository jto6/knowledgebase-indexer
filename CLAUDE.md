# KBI (Knowledgebase Indexer) Project

**IMPORTANT: Always check ~/.claude/commands directory for custom slash commands before attempting to execute them as bash commands. Slash commands (starting with /) are Claude Code custom commands, not bash commands.**

## Project Overview

A Python implementation of the Knowledgebase Indexer that builds navigational indexes over collections of structured files. It computes a render-independent index model with four navigation views — File System, Keyword, Tag, and Word — then emits it through a renderer (Freeplane `.mm` mind map by default; a Markdown / Claude-facing renderer is planned).

## Primary Requirement: Follow the PRD

**CRITICAL**: Always reference and follow `docs/kbi_PRD.md` when implementing any feature or making changes. The PRD contains detailed requirements with specific identifiers (e.g., R-KW-SYNTAX-007) that must be implemented exactly as specified.

### Before Making Changes:
1. Read the relevant section of `docs/kbi_PRD.md`
2. Identify the specific requirement IDs that apply
3. Implement according to the PRD specifications
4. Reference the requirement IDs in commit messages and code comments

## Technology Stack

- **Language**: Python 3
- **Configuration**: YAML files
- **Renderers**: Freeplane `.mm` mind map (default); Markdown / Claude-facing (planned)
- **File Processing**: XML parsing, Markdown parsing
- **Dependencies**: See `requirements.txt`

## Architecture

The system follows a modular design with clear separation of concerns:

### Core Components
- `kbi.py`: Main application entry point and orchestration
- `config.py`: Configuration loading and validation
- `core_handlers.py`: Base classes and common functionality
- `search.py`: Hierarchical context-sensitive search engine
- `keywords.py`: Keyword file parsing and processing
- `mindmap_generator.py`: Freeplane XML generation
- `logging_config.py`: Logging configuration and management

### File Handlers (Plugin Architecture)
- `handlers/freeplane_handler.py`: Freeplane .mm file processing
- `handlers/markdown_handler.py`: Markdown file processing
- Extensible for additional file types

## Key Features

1. **File System Index**: Hierarchical directory structure mirroring physical layout
2. **Keyword Index**: Context-sensitive regex search with hierarchical scope narrowing
3. **Tag Index**: Tag-based file organization (when tags are present)
4. **Configurable File Discovery**: Glob patterns for inclusion/exclusion
5. **Plugin-based File Handlers**: Extensible architecture for different file types

## Configuration

- Default locations: `./configs/kbi.yml`, `./config/kbi.yml`, `./kbi.yml`, `~/.config/kbi/config.yml`
- Example configuration: `./configs/example.yml`
- YAML format with schema validation
- Configurable directories, file types, keyword files, and output settings

## Common Commands

```bash
# Generate index with default settings
python3 kbi.py

# Enable debug output
python3 kbi.py --debug

# Use specific configuration
python3 kbi.py --config myconfig.yml

# Specify output file
python3 kbi.py --output my_index.mm

# Generate sample files
python3 kbi.py --sample-config
python3 kbi.py --sample-keywords
```

## Testing

Always test changes with:
```bash
python3 kbi.py --debug
```

## Directory Structure

```
kbi/
├── kbi.py                 # Main application entry point
├── config.py             # Configuration management
├── core_handlers.py      # Base classes and utilities
├── search.py            # Search engine implementation
├── keywords.py          # Keyword file processing
├── mindmap_generator.py # XML output generation
├── logging_config.py    # Logging configuration
├── handlers/            # File type handlers
│   ├── freeplane_handler.py
│   └── markdown_handler.py
├── tests/              # Test files
├── configs/           # Configuration files
│   ├── example.yml   # Example configuration
│   └── keywords.txt  # Sample keyword file
├── docs/             # Project documentation
│   ├── CODING_STYLE.md
│   ├── kbi_PRD.md     # Product Requirements Document
│   ├── PRD_CHECKLIST.md
│   └── TESTING_GUIDE.md
└── requirements.txt   # Python dependencies
