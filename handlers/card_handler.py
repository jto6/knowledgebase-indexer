#!/usr/bin/env python3
"""Card file handler: parses distilled `.kb.md` knowledge-base cards.

A card is a Markdown file with YAML frontmatter (id, slug, title, domain, tags,
builds_on, defines, meta, source) whose body's first blockquote is the one-line
essence. Cards are the distilled, curated unit of the knowledge base. This
handler reads them *card-aware* — tags and index labels come from the
frontmatter (the card's title), not from the filename or body hashtags — while
reusing Markdown body parsing so search and word indexing still work over the
card's content.

Scoping note: this handler only makes `card` a selectable file type (keyed on
the compound extension `.kb.md`). What gets indexed is decided by which file
types a config enables — enable only `card` for a distilled cross-repo catalog,
or enable `card` + `markdown` + ... for a deep within-repo index.

See docs/kbi_PRD.md and docs/DESIGN_PRINCIPLES_AND_DECISIONS.md §5 (card schema).
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.append(str(Path(__file__).parent.parent))

from handlers.markdown_handler import MarkdownHandler

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a declared dependency
    yaml = None


CARD_SUFFIX = '.kb.md'


class CardHandler(MarkdownHandler):
    """Handler for distilled knowledge-base cards (`*.kb.md`)."""

    def can_handle(self, file_path: str) -> bool:
        """Match cards by their compound `.kb.md` suffix (not just `.md`)."""
        path = Path(file_path)
        return path.name.endswith(CARD_SUFFIX) and path.exists()

    def validate_file(self, file_path: str) -> bool:
        """Validate by suffix match; the base class checks `path.suffix`, which
        is only `.md` for a card, so it must be overridden."""
        path = Path(file_path)
        if not path.exists():
            return False
        extensions = self.config.get('extensions', [CARD_SUFFIX])
        return any(path.name.endswith(ext) for ext in extensions)

    # -- card-aware frontmatter parsing --------------------------------------

    def _split_frontmatter(self, content: str):
        """Return (frontmatter_dict, body). Empty dict if no frontmatter."""
        if not content.startswith('---\n'):
            return {}, content
        end = content.find('\n---', 4)
        if end == -1:
            return {}, content
        fm_text = content[4:end]
        body = content[end + 4:].lstrip('\n')
        fm = {}
        if yaml is not None:
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception:
                fm = {}
        return fm, body

    def _essence(self, body: str) -> str:
        """The first blockquote block after the title is the card's essence."""
        collected = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('>'):
                collected.append(stripped.lstrip('>').strip())
            elif collected:
                break
        return ' '.join(collected).strip()

    def get_card_record(self, file_path: str) -> Dict[str, Any]:
        """Parse frontmatter + essence into a record for the catalog/slices.

        Carries the card-specific fields (domain, builds_on, defines, meta, ...)
        that increment B will render as per-domain slices, cross-edges, and a
        term index. Increment A only consumes `title` and `tags`.
        """
        try:
            content = Path(file_path).read_text(encoding='utf-8')
        except Exception:
            return {'file_path': file_path, 'title': Path(file_path).name}
        fm, body = self._split_frontmatter(content)
        record: Dict[str, Any] = dict(fm)
        record['file_path'] = file_path
        record.setdefault('title', Path(file_path).name)
        record['essence'] = self._essence(body)
        return record

    def card_label(self, file_path: str) -> str:
        """Human-facing label for index nodes: the card title."""
        return self.get_card_record(file_path).get('title') or Path(file_path).name

    # -- tags: frontmatter-driven, labeled by the card title -----------------

    def extract_tags(self, file_path: str) -> Dict[str, List[tuple]]:
        """Tags come only from frontmatter `tags`; the index label is the card
        title (so the Tag Index shows titles, not `Plan.kb.md`)."""
        record = self.get_card_record(file_path)
        label = record.get('title') or Path(file_path).name
        tags = record.get('tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        tag_map: Dict[str, List[tuple]] = {}
        for tag in tags:
            tag = str(tag).strip()
            if tag:
                tag_map.setdefault(tag, []).append((file_path, '', label))
        return tag_map
