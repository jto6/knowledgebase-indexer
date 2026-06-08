# Knowledge Base System — Tutorial

A quick, example-driven getting-started guide. It is not exhaustive — see
`REFERENCE.md` for the full schema and semantics.

## The two sides

- **Author cards** with `/kb-card` *inside a content repo*. Cards live in `.kb/`
  folders and are committed with that repo.
- **Build the catalog** with `kbi` (run separately). It reads cards read-only and
  writes per-domain *slices* that consumers read.

One-time per area: create an area config so `/kb-card` knows the domain and how to
distill. Everything else is optional overrides.

```yaml
# <area-root>/.kb/kb.yml
domain: spiritual
profile: reflective          # reflective = include key quotes; standard = none
seed_tags: [faith, grace, discipleship]
```

## Use case 1 — a small repo → one card

For a small, single-topic repo, one card covers it.

```bash
cd ~/dev/some-small-repo
# (create .kb/kb.yml with a domain, e.g. domain: technical)
/kb-card                     # source defaults to the current directory
```

Result: `./.kb/<name>.kb.md` (one card) and `./.kb/cards.yml`.

## Use case 2 — a sprawling but organized repo → a card per item

When each subdirectory is one coherent item (e.g. BSFL: one lesson per folder),
recurse and let each leaf get its own card.

```bash
cd ~/dev/BSFL
# area .kb/kb.yml: domain: spiritual, profile: reflective
/kb-card -r "Fall 2025"      # walk the tree; one card per lesson folder
```

Each lesson folder gets `<folder>/.kb/Plan.kb.md` + `cards.yml`. To target one
lesson: `cd` into it and run `/kb-card`.

## Use case 3 — a dense report → split into several cards

A long, multi-topic report should become several cards. Allow splitting in that
subtree, then review the proposed split before authoring.

```yaml
# reports/.kb/kb.yml  (inherits domain/profile from the area root)
card_split: auto
```

```bash
cd ~/dev/research/SDV-research/reports
/kb-card -plan Hypervisor_Technologies.md     # propose the split; STOP for review
#   → writes cards.yml with the proposed sections; review/adjust it
/kb-card Hypervisor_Technologies.md           # author the cards per cards.yml
```

Want it deeper or shallower? Use the density dial (or a `-cards` ceiling):

```bash
/kb-card -density fine Hypervisor_Technologies.md   # ~ one card per section
/kb-card -cards 8 Hypervisor_Technologies.md        # at most 8 (never pads to 8)
```

`-cards N` is a **maximum**, not a target — it never invents topics to reach N.
To go deeper on just one section, add a `density_overrides` entry to that
directory's `cards.yml` during the `-plan` review.

## Use case 4 — build the catalog and read it

Write a catalog config that scopes to cards only (`card` file type) and uses the
markdown renderer, then run `kbi`.

```yaml
# configs/catalog.yml (in the kbi repo)
directories:
  include: ["/home/jon/dev/BSFL", "/home/jon/dev/research/SDV-research"]
  exclude: ["**/.git/**", "**/__pycache__/**"]
keywords: { files: [] }
output: { file: "/home/jon/dev/kb/index", format: "markdown" }
file_types:
  card: { extensions: [".kb.md"], handler: "CardHandler" }
```

```bash
cd ~/dev/kbi
python3 kbi.py --config configs/catalog.yml
#   → ~/dev/kb/index/<domain>.md  (one slice per domain) + INDEX.md
```

Open a slice (e.g. `~/dev/kb/index/spiritual.md`) to see each card's title,
essence, tags, `builds_on`, `defines`, and path — the index a consumer scans.

### Or render a mind map instead

The same index model also renders to a Freeplane `.mm` mind map (the human
navigation view). Switch `format` to `freeplane` and point `output.file` at a
`.mm` file — same card-only scope:

```yaml
output: { file: "/home/jon/dev/kb/catalog.mm", format: "freeplane" }
file_types:
  card: { extensions: [".kb.md"], handler: "CardHandler" }
```

```bash
python3 kbi.py --config configs/catalog-mm.yml      # → /home/jon/dev/kb/catalog.mm
```

Open `catalog.mm` in Freeplane to browse the File System, Tag, and Word index
branches over your cards.

To deep-index **one repo's full content** (not just cards — the original kbi
use), scope to that repo and enable all file types:

```yaml
directories: { include: ["/home/jon/dev/research/SDV-research"] }
keywords: { files: [] }
output: { file: "/home/jon/dev/research/SDV-research/index.mm", format: "freeplane" }
file_types:
  card:      { extensions: [".kb.md"],          handler: "CardHandler" }
  markdown:  { extensions: [".md", ".markdown"], handler: "MarkdownHandler" }
  freeplane: { extensions: [".mm"],             handler: "FreeplaneHandler" }
```

This indexes every document (and parses cards card-aware), producing a full
local navigation map of the repo.

## Use case 5 — wire a consumer (e.g. a council member)

The retrieval protocol is shared once; each member just declares its slice.

```markdown
<!-- advisor/CLAUDE.md (shared, once) -->
## Knowledge Base Access
Slice location: /home/jon/dev/kb/index/<domain>.md
Protocol: scan the slice → open the 1–3 relevant cards → follow `source:` only
for full detail.
```

```markdown
<!-- advisor/pastor/CLAUDE.md (per-member subscription) -->
## Knowledge Base Access
Subscribed slice: /home/jon/dev/kb/index/spiritual.md — apply the council's
shared retrieval protocol.
```

A member-only session picks up the shared protocol automatically (CLAUDE.md loads
up the directory tree).

## Use case 6 — update when content changes

Edit a source, then re-run `/kb-card` over the area; it **reconciles** against
`cards.yml` and only acts on what changed:

```bash
/kb-card -r reports/          # refresh drifted cards, re-segment broken
                              # boundaries, flag orphans, propose new sections
python3 ~/dev/kbi/kbi.py --config configs/catalog.yml   # regenerate slices
```

You never redo settled decisions — locked boundaries persist; only genuinely
changed content is re-reviewed. (See `REFERENCE.md` §4.4 for the reconcile
outcomes.)

## Cheat sheet

| Goal                          | Command                                      |
|-------------------------------|----------------------------------------------|
| One card for the current dir  | `/kb-card`                                   |
| A card per item in a tree     | `/kb-card -r <root>`                         |
| Propose a split, review first | `/kb-card -plan <file>`                      |
| Split deeper / cap the count  | `/kb-card -density fine <file>` / `-cards N` |
| Re-segment a changed source   | `/kb-card -resegment <file>`                 |
| Build the catalog             | `python3 kbi.py --config <catalog.yml>`      |
