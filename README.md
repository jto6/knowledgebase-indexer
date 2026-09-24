# Knowledgebase Indexer

A Python implementation of the Knowledgebase Indexer that builds navigational indexes over collections of structured files. It computes a render-independent index model and emits it through renderers — Freeplane `.mm` mind maps and Markdown (Claude-facing) per-domain slices. See the documentation below.

## Features

- **File System Index**: Hierarchical directory view mirroring physical structure
- **Keyword Index**: Context-sensitive search with hierarchical scope narrowing
- **Tag Index**: Tag-based file organization
- **Extensible Architecture**: Plugin-based file handlers
- **Pluggable Renderers**: Freeplane `.mm` mind maps and Markdown (Claude-facing) per-domain slices

## Documentation

- `docs/TUTORIAL.md` — getting-started, example-driven walkthrough of each use case
- `docs/REFERENCE.md` — full reference: meta-file schemas (card / `kb.yml` / `segmentation.yml`), the `/kb-card` command, and the catalog config
- `docs/DESIGN_PRINCIPLES_AND_DECISIONS.md` — architecture, principles, and the rationale behind the decisions
- `docs/kbi_PRD.md` — the indexer engine requirements

## Installation

kbi requires [uv](https://docs.astral.sh/uv/getting-started/installation/) as a system prerequisite. There is no per-checkout install step.

`kbi.py`, `run_tests.py` and `doc_to_markdown.py` declare their dependencies inline (a PEP 723 `# /// script` header) and use the shebang `#!/usr/bin/env -S uv run --script`. Running one directly makes uv build a matching isolated environment on first use, cache it, and run the script in it. Your shell and any active virtual environment are left alone.

Run the scripts directly (`./kbi.py ...` or `~/dev/kbi/kbi.py ...`). `./kbi.py` bypasses the shebang and therefore uv, and fails unless that interpreter happens to have the dependencies.

When changing dependencies, update the script headers and `requirements.txt` together. The Makefile's pytest and lint targets use `requirements.txt`.

## Usage

### Basic Usage

```bash
# Generate an index from a config file (required positional argument)
./kbi.py configs/myconfig.yml

# Enable debug output
./kbi.py configs/myconfig.yml --debug

# Specify output file
./kbi.py configs/myconfig.yml --output my_index.mm
```

### Refreshing knowledge cards (`--update-cards`)

```bash
# Refresh stale card sets before indexing: scans managed directories
# (.kb/segmentation.yml), computes a per-directory content delta, and hands
# it to `claude -p '/kb-card --delta <file>'` for each stale directory.
# Successful refreshes in git repositories auto-commit only the .kb/ paths.
./kbi.py configs/myconfig.yml --update-cards

# Same, without the .kb auto-commits
./kbi.py configs/myconfig.yml --update-cards --no-commit
```

See `docs/REFERENCE.md` §5.7 for the staleness rules and delta format, and
`docs/UPDATE_TOKEN_EFFICIENCY.md` for the design rationale.

### Helper subcommands

```bash
# Search exactly the files an index config covers (ripgrep, else grep)
./kbi.py search configs/myconfig.yml "<regex>" -i

# Canonical source_hash (sha256 of raw bytes) per file
./kbi.py hash <file>...

# Mechanically refresh a .kb/segmentation.yml manifest's derivable fields
# (source_hash values, dir_hash, dir_fingerprint, updated)
./kbi.py manifest-sync [<dir>]

# Audit segmentation decisions made headlessly by --update-cards runs
./kbi.py decisions [<root>]
```

### Sample Files

Generate sample configuration and keyword files:

```bash
# Create sample configuration
./kbi.py --sample-config

# Create sample keyword file
./kbi.py --sample-keywords
```

## Configuration

The application uses YAML configuration files. Default locations searched:

1. Command line `--config` argument
2. `./configs/kbi.yml` or `./configs/kbi.yaml`
3. `./config/kbi.yml` or `./config/kbi.yaml`
4. `./kbi.yml` or `./kbi.yaml`
5. `~/.config/kbi/config.yml`

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
    - "configs/keywords.txt"

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

Produces a render-independent index model, emitted as a Freeplane `.mm` mind map by default (a Markdown renderer is planned), with navigation branches:

1. **File System Index**: Directory structure with file hierarchy
2. **Keyword Index**: Search results organized by keyword sequences
3. **Tag Index**: Files grouped by extracted tags

## Examples

Process markdown and mind map files in current directory:
```bash
./kbi.py --debug
```

Generate index with custom keyword searches:
```bash
echo -e "Documentation\n\tAPI\n\t\tapi:reference\n\tGuides\n\t\ttutorial:beginner" > configs/keywords.txt
./kbi.py --debug
```
