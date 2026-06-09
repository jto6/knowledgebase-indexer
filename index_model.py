#!/usr/bin/env python3
"""The unified index model.

kbi builds one render-independent model from whatever the handlers extract, then
a renderer serializes it. The model is the *superset* of what handlers can encode:
generic views (file system, keyword, word) plus optional views populated only when
some indexed file supplies the data (tags, and the card-only dependencies and
glossary). The model is partitioned by **domain**.

`output.format` selects only the serialization; it never selects the model.
See docs/DESIGN_PRINCIPLES_AND_DECISIONS.md (D16).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a declared dependency
    yaml = None


# --- Provenance marker ------------------------------------------------------
# kbi stamps every index it writes (.mm and .md) with an invisible marker so a
# later run can recognise its own output and refuse to re-index it (avoiding the
# self-recursion where a generated index inside a scanned tree gets ingested as
# source). The marker is an XML/HTML comment — invisible in Freeplane and in
# rendered markdown, and tolerated by Freeplane's loader (which writes its own
# comment in the same position). The token must never contain "--" (illegal
# inside an XML comment), so the timestamp uses single-hyphen ISO-8601.
KBI_MARKER_TOKEN = "kbi:generated"
KBI_MARKER_VERSION = "1"
# Only the head of a file is scanned for the marker; outputs carry it at the top.
_MARKER_SCAN_BYTES = 4096


def marker_comment() -> str:
    """The provenance comment line written into generated indexes (.mm and .md).

    Valid as both an XML comment (Freeplane) and an HTML comment (markdown).
    """
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"<!-- {KBI_MARKER_TOKEN} v={KBI_MARKER_VERSION} at={stamp} -->"


def file_is_generated(path, max_bytes: int = _MARKER_SCAN_BYTES) -> bool:
    """True if `path` carries the kbi provenance marker in its head.

    Reads only the first `max_bytes`; unreadable files are treated as not ours.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return KBI_MARKER_TOKEN in fh.read(max_bytes)
    except OSError:
        return False


# The bucket name used for domainless files when *some* files have a domain.
NONE_DOMAIN = "none"

# Canonical view names (also the keys under `output.views`).
VIEW_FILE_SYSTEM = "file_system"
VIEW_KEYWORD = "keyword"
VIEW_TAG = "tag"
VIEW_WORD = "word"
VIEW_DEPENDENCIES = "dependencies"
VIEW_GLOSSARY = "glossary"
ALL_VIEWS = [VIEW_FILE_SYSTEM, VIEW_KEYWORD, VIEW_TAG, VIEW_WORD,
             VIEW_DEPENDENCIES, VIEW_GLOSSARY]


@dataclass
class CardGroup:
    """FS-view grouping of cards that share a source.

    Each entry in `DomainIndex.card_groups` is keyed by the resolved absolute
    source path (file or directory) and holds:
    - annotation: the one-line essence to annotate the source node with (empty
      string = no annotation).
    - hidden_card: path of the `kind: file_summary` card whose essence is the
      annotation and which the renderer must NOT render as a leaf. None when
      the annotation came from a lone topic card (topic cards are always
      rendered as leaves even when they supply the annotation).
    - cards: list of (label, card_path) tuples for ALL cards (including the
      file_summary card if any). Renderers filter out `hidden_card`.
    """
    annotation: str = ""
    hidden_card: Optional[str] = None    # absolute path of file_summary card to suppress
    cards: List[tuple] = field(default_factory=list)   # [(label, card_path)]


@dataclass
class DomainIndex:
    """All views for one domain partition (or the single unpartitioned bucket)."""
    name: Optional[str]                                  # domain, NONE_DOMAIN, or None (unpartitioned)
    files: List[str] = field(default_factory=list)
    file_system: Dict[str, list] = field(default_factory=dict)   # file -> root nodes (non-card files)
    card_groups: Dict[str, CardGroup] = field(default_factory=dict)  # source_path -> CardGroup
    keyword_entries: list = field(default_factory=list)
    tags: Dict[str, list] = field(default_factory=dict)          # tag -> [(file, node_id, label)]
    words: Dict[str, dict] = field(default_factory=dict)         # word -> {file: matches}
    dependencies: list = field(default_factory=list)             # [(card_record, [(label, path)])]
    glossary: Dict[str, dict] = field(default_factory=dict)      # term -> card_record


@dataclass
class IndexModel:
    """Domains → their views. `partitioned` is False when no file has a domain."""
    domains: Dict[Optional[str], DomainIndex] = field(default_factory=dict)
    partitioned: bool = False

    def ordered_domains(self):
        """Domains in a stable render order: real domains alphabetically, NONE_DOMAIN last."""
        names = [n for n in self.domains if n not in (None, NONE_DOMAIN)]
        names.sort(key=lambda s: s.lower())
        if NONE_DOMAIN in self.domains:
            names.append(NONE_DOMAIN)
        if None in self.domains:
            names.append(None)
        return [(n, self.domains[n]) for n in names]


def area_domain_for_dir(directory: Path) -> Optional[str]:
    """Walk up from a directory to the nearest `.kb/kb.yml` and return its `domain`.

    kbi reads `kb.yml` only for this one field — to learn the domain partition for
    non-card files. Everything else in `kb.yml` is author-side and ignored.
    """
    if yaml is None:
        return None
    try:
        cur = directory.resolve()
    except Exception:
        cur = directory
    while True:
        kbyml = cur / ".kb" / "kb.yml"
        if kbyml.exists():
            try:
                data = yaml.safe_load(kbyml.read_text(encoding="utf-8")) or {}
                domain = data.get("domain")
                return str(domain).strip() if domain else None
            except Exception:
                return None
        if cur.parent == cur:
            return None
        cur = cur.parent


def resolve_domain(file_path: str, card_record: Optional[dict]) -> Optional[str]:
    """A file's domain: card frontmatter `domain`, else nearest `kb.yml` domain, else None."""
    if card_record and card_record.get("domain"):
        return str(card_record["domain"]).strip()
    return area_domain_for_dir(Path(file_path).parent)


def view_enabled(config: Dict[str, Any], view: str, renderer: str) -> bool:
    """Whether a view is serialized: `output.views.<view>` of auto|on|off overrides
    the per-renderer default. Default is include-if-data for every view, except the
    word index which is **opt-in** (default off for both renderers) — it is verbose,
    heavy to build, and superseded by `kbi search`. Enable with `views.word: on`."""
    default = True
    if view == VIEW_WORD:
        default = False
    setting = ((config.get("output", {}) or {}).get("views", {}) or {}).get(view, "auto")
    if setting == "on":
        return True
    if setting == "off":
        return False
    return default
