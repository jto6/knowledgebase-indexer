---
id: adc1481c-1b12-400f-b681-4f81ebc9f034
slug: doc-to-markdown
title: Document to Markdown Converter
source: "[doc_to_markdown.py](<../doc_to_markdown.py>)"
domain: technical
tags: [kbi, utility, cli, python, anthropic-api, document-conversion]
created: 2026-07-17
updated: 2026-07-17
---

# Document to Markdown Converter

> `doc_to_markdown.py` is a standalone CLI utility that uploads a PDF/Word/PowerPoint file to the Claude Files API and asks Claude to convert it into analysis-optimized markdown.

## Core Concepts

- **Two-step API flow** (`DocumentConverter`): `upload_file()` posts the document to `/v1/files` (via the `files-api-2025-04-14` beta header) to get a `file_id`, then `convert_to_markdown()` sends a `/v1/messages` request referencing that `file_id` as a `document` content block alongside a conversion-instruction prompt
- **Supported inputs**: `.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx`, capped at 500MB; `validate_file()` checks existence, type, and size before upload
- **Conversion prompt** (`_get_conversion_prompt()`): instructs Claude to preserve structure/hierarchy, tables, images (as `[Image: description]`), formatting, and metadata, and to optimize headings/wording for later search and Q&A
- **Output**: `save_markdown()` writes the result with a YAML frontmatter header (`title`, `source_file`, `converted_on`, `converter`, `original_format`) prepended to the converted body
- **Not integrated with kbi's own handler layer** — this is a standalone pre-processing script (run manually to produce a `.md` file), not a `FileHandler` plugin; its output would need a subsequent `/kb-card` pass to become a card
- **CLI**: `doc_to_markdown.py <file_path> [--output <path>] [--api-key <key>] [--debug]`; API key from `--api-key` or `ANTHROPIC_API_KEY`
- **Known gap**: hardcodes `model: claude-3-5-sonnet-20241022` and a fixed `max_tokens: 8192`, so large converted documents can be truncated
