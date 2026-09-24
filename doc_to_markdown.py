#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "requests>=2.31.0",
# ]
# ///
"""
Document to Markdown Converter

Uploads PDF, Word, or PowerPoint files to Claude.ai and converts them to rich markdown
format optimized for later analysis and question answering with Claude Code.

Usage:
    ./doc_to_markdown.py <file_path> [--output <output_path>] [--api-key <key>]

Environment Variables:
    ANTHROPIC_API_KEY: Your Anthropic API key (required if not passed via --api-key)

Supported file types:
    - PDF (.pdf)
    - Word (.doc, .docx)
    - PowerPoint (.ppt, .pptx)
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentConverter:
    """Handles document upload to Claude.ai and conversion to markdown."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx'}
    API_BASE_URL = "https://api.anthropic.com/v1"
    BETA_HEADER = "files-api-2025-04-14"
    
    def __init__(self, api_key: str):
        """Initialize converter with API key."""
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'anthropic-beta': self.BETA_HEADER
        })
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate that file exists and has supported extension."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            return False
        
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file type: {file_path.suffix}")
            logger.error(f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}")
            return False
        
        file_size = file_path.stat().st_size
        max_size = 500 * 1024 * 1024  # 500 MB
        if file_size > max_size:
            logger.error(f"File too large: {file_size / (1024*1024):.1f}MB (max 500MB)")
            return False
        
        logger.info(f"File validated: {file_path.name} ({file_size / (1024*1024):.1f}MB)")
        return True
    
    def upload_file(self, file_path: Path) -> Optional[str]:
        """Upload file to Claude Files API and return file ID."""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, self._get_mime_type(file_path))}
                
                logger.info(f"Uploading {file_path.name}...")
                response = self.session.post(f"{self.API_BASE_URL}/files", files=files)
                
                if response.status_code == 200:
                    file_data = response.json()
                    file_id = file_data.get('id')
                    logger.info(f"File uploaded successfully. ID: {file_id}")
                    return file_id
                else:
                    logger.error(f"Upload failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None
    
    def convert_to_markdown(self, file_id: str, original_filename: str) -> Optional[str]:
        """Send file to Claude for conversion to markdown."""
        conversion_prompt = self._get_conversion_prompt(original_filename)
        
        try:
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 8192,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "file",
                                    "file_id": file_id
                                }
                            },
                            {
                                "type": "text",
                                "text": conversion_prompt
                            }
                        ]
                    }
                ]
            }
            
            logger.info("Converting document to markdown...")
            response = self.session.post(
                f"{self.API_BASE_URL}/messages",
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                markdown_content = result['content'][0]['text']
                logger.info("Conversion completed successfully")
                return markdown_content
            else:
                logger.error(f"Conversion failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return None
    
    def save_markdown(self, content: str, output_path: Path, original_file: Path) -> bool:
        """Save markdown content to file with metadata header."""
        try:
            # Add metadata header
            metadata_header = f"""---
title: "{original_file.stem}"
source_file: "{original_file.name}"
converted_on: "{datetime.now().isoformat()}"
converter: "doc_to_markdown.py"
original_format: "{original_file.suffix[1:].upper()}"
---

"""
            
            full_content = metadata_header + content
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"Markdown saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file extension."""
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        }
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    def _get_conversion_prompt(self, filename: str) -> str:
        """Generate conversion prompt optimized for Claude Code analysis."""
        return f"""Please convert this document ({filename}) to rich markdown format that will be optimal for later analysis and question answering with Claude Code.

Requirements:

1. **Structure & Hierarchy**:
   - Use proper markdown headers (# ## ### ####) to maintain document hierarchy
   - Preserve the logical flow and organization of the original document
   - Create a table of contents if the document has multiple sections

2. **Content Preservation**:
   - Maintain all important text content, including footnotes and references
   - Preserve tables using markdown table syntax
   - Include image descriptions in [Image: description] format when images are present
   - Keep mathematical formulas and technical notation clear
   - Preserve code blocks and technical specifications

3. **Formatting for Analysis**:
   - Use **bold** for important terms and key concepts
   - Use *italics* for emphasis and definitions
   - Use `code formatting` for technical terms, file names, and commands
   - Create bulleted and numbered lists where appropriate
   - Use blockquotes (>) for important quotes or callouts

4. **Metadata & Context**:
   - Include key document metadata (author, dates, version) if present
   - Preserve chapter/section numbering schemes
   - Maintain cross-references and internal links where possible

5. **Optimization for Q&A**:
   - Structure content so it's easy to search and reference specific sections
   - Include relevant keywords and terms that might be searched for
   - Ensure headings are descriptive and searchable
   - Break up large paragraphs into more digestible chunks when appropriate

Please provide only the markdown content without any preamble or explanation."""

def main():
    """Main function to handle command line arguments and orchestrate conversion."""
    parser = argparse.ArgumentParser(
        description="Convert PDF, Word, or PowerPoint files to markdown using Claude.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./doc_to_markdown.py document.pdf
    ./doc_to_markdown.py presentation.pptx --output my_notes.md
    ./doc_to_markdown.py report.docx --api-key sk-ant-xxxxx
        """
    )
    
    parser.add_argument(
        'file_path',
        help='Path to the document file (PDF, DOC, DOCX, PPT, PPTX)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output markdown file path (default: same name with .md extension)'
    )
    
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY environment variable)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get API key from args or environment
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key")
        return 1
    
    # Validate and setup paths
    input_path = Path(args.file_path)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.md')
    
    # Initialize converter and process file
    converter = DocumentConverter(api_key)
    
    # Validate file
    if not converter.validate_file(input_path):
        return 1
    
    # Upload file
    file_id = converter.upload_file(input_path)
    if not file_id:
        return 1
    
    # Convert to markdown
    markdown_content = converter.convert_to_markdown(file_id, input_path.name)
    if not markdown_content:
        return 1
    
    # Save markdown file
    if converter.save_markdown(markdown_content, output_path, input_path):
        logger.info(f"Document successfully converted to markdown: {output_path}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())