#!/usr/bin/env python3
"""Markdown slice renderer: the Claude-facing catalog view.

Consumes the card records produced by CardHandler and emits one compact,
greppable Markdown index per domain (a "slice"), plus an overview INDEX.md.
A consumer (a council member, a project, an ad-hoc session) subscribes to a
domain by reading its slice, scanning titles/essences/tags, and opening the
relevant cards; `source:` links lead to the original material.

This is a second renderer over the index model (one model, many renderers); the
Freeplane `.mm` renderer remains the human navigation view. See
docs/DESIGN_PRINCIPLES_AND_DECISIONS.md (D9, D12, §7) and docs/kbi_PRD.md.
"""

from pathlib import Path
from typing import Dict, List, Any, Iterable


def _as_list(value: Any) -> List[str]:
    """Normalize a frontmatter field to a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(',') if v.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


class MarkdownSliceRenderer:
    """Render per-domain Markdown slices from card records."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _domain_of(record: Dict[str, Any]) -> str:
        return str(record.get('domain') or 'uncategorized').strip() or 'uncategorized'

    @staticmethod
    def _title_of(record: Dict[str, Any]) -> str:
        return record.get('title') or Path(record.get('file_path', 'card')).name

    def _build_indexes(self, records: List[Dict[str, Any]]):
        """slug -> record (for builds_on resolution) and term -> record (glossary)."""
        by_slug: Dict[str, Dict[str, Any]] = {}
        by_term: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            slug = rec.get('slug')
            if slug:
                by_slug[str(slug)] = rec
            for term in _as_list(rec.get('defines')):
                by_term[term] = rec
        return by_slug, by_term

    def _resolve_link(self, ref: str, by_slug: Dict[str, Dict[str, Any]]) -> str:
        """Render a card reference (slug) as its title when known, else the raw slug."""
        target = by_slug.get(ref)
        return self._title_of(target) if target else ref

    # -- rendering -----------------------------------------------------------

    def _render_slice(self, domain: str, records: List[Dict[str, Any]],
                      by_slug: Dict[str, Dict[str, Any]]) -> str:
        records = sorted(records, key=lambda r: self._title_of(r).lower())
        lines: List[str] = []
        lines.append(f"# Knowledge Base — {domain}")
        lines.append("")
        lines.append(f"> {len(records)} card(s). Distilled index for retrieval — open a "
                     f"card for full detail, follow its `source` for the original material.")
        lines.append("")

        # Cards
        lines.append("## Cards")
        lines.append("")
        for rec in records:
            lines.append(f"- {self._title_of(rec)}")
            essence = (rec.get('essence') or '').strip()
            if essence:
                lines.append(f"\t- {essence}")
            tags = _as_list(rec.get('tags'))
            if tags:
                lines.append(f"\t- tags: {', '.join(tags)}")
            builds_on = _as_list(rec.get('builds_on'))
            if builds_on:
                resolved = '; '.join(self._resolve_link(b, by_slug) for b in builds_on)
                lines.append(f"\t- builds on: {resolved}")
            defines = _as_list(rec.get('defines'))
            if defines:
                lines.append(f"\t- defines: {', '.join(defines)}")
            lines.append(f"\t- card: {rec.get('file_path', '')}")
            sources = _as_list(rec.get('source'))
            if sources:
                lines.append(f"\t- source: {', '.join(sources)}")
        lines.append("")

        # Tag index (content-centered clustering within the domain)
        tag_map: Dict[str, List[str]] = {}
        for rec in records:
            for tag in _as_list(rec.get('tags')):
                tag_map.setdefault(tag, []).append(self._title_of(rec))
        if tag_map:
            lines.append("## Tags")
            lines.append("")
            for tag in sorted(tag_map, key=str.lower):
                lines.append(f"- {tag}")
                for title in sorted(tag_map[tag], key=str.lower):
                    lines.append(f"\t- {title}")
            lines.append("")

        # Glossary (terms this domain's cards define)
        term_map: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            for term in _as_list(rec.get('defines')):
                term_map[term] = rec
        if term_map:
            lines.append("## Glossary (defined terms)")
            lines.append("")
            for term in sorted(term_map, key=str.lower):
                rec = term_map[term]
                lines.append(f"- {term} — {self._title_of(rec)} ({rec.get('file_path', '')})")
            lines.append("")

        return '\n'.join(lines).rstrip() + '\n'

    def _render_overview(self, by_domain: Dict[str, List[Dict[str, Any]]]) -> str:
        lines: List[str] = []
        lines.append("# Knowledge Base — Catalog")
        lines.append("")
        lines.append("> Per-domain distilled card slices. Read a domain's slice to "
                     "find and open relevant cards.")
        lines.append("")
        lines.append("## Domains")
        lines.append("")
        for domain in sorted(by_domain, key=str.lower):
            n = len(by_domain[domain])
            lines.append(f"- [{domain}]({domain}.md) — {n} card(s)")
        return '\n'.join(lines).rstrip() + '\n'

    def render(self, records: Iterable[Dict[str, Any]]) -> List[str]:
        """Write one slice per domain plus an overview INDEX.md. Returns paths."""
        records = list(records)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for rec in records:
            by_domain.setdefault(self._domain_of(rec), []).append(rec)

        by_slug, _ = self._build_indexes(records)

        written: List[str] = []
        for domain, domain_records in by_domain.items():
            path = self.output_dir / f"{domain}.md"
            path.write_text(self._render_slice(domain, domain_records, by_slug), encoding='utf-8')
            written.append(str(path))

        overview = self.output_dir / "INDEX.md"
        overview.write_text(self._render_overview(by_domain), encoding='utf-8')
        written.append(str(overview))

        return written
