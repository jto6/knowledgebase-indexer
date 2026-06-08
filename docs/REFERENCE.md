# Knowledge Base System — Reference Manual

This is the reference for the knowledge-base system: the meta-file formats
(schema, syntax, and semantics), the `/kb-card` authoring command, and the `kbi`
indexer/catalog. For *why* the system is shaped this way, see
`DESIGN_PRINCIPLES_AND_DECISIONS.md`; for worked examples, see `TUTORIAL.md`.

## Concepts and artifacts

The system has three layers: **cards** (distilled units of knowledge, authored
and distributed), **slices** (generated per-domain indexes that consumers read),
and the **catalog** (the cross-repo aggregate). Two sides operate on them:

- **Author-side** — `/kb-card`, run inside a content repo, writes cards and the
  segmentation manifest. These are committed with that repo.
- **Catalog-side** — `kbi`, run separately, reads cards *read-only* and generates
  the catalog (slices and/or a mind map). It never writes into a content repo.

Artifacts and where they live:

| Artifact              | Path                          | Written by          | Read by                  |
|-----------------------|-------------------------------|---------------------|--------------------------|
| Card                  | `<dir>/.kb/<name>.kb.md`      | `/kb-card` (author) | `kbi`, humans, consumers |
| Area config           | `<area>/.kb/kb.yml`           | author (once)       | `/kb-card`               |
| Segmentation manifest | `<dir>/.kb/cards.yml`         | `/kb-card`          | `/kb-card`               |
| Catalog config        | a `kbi` config file (YAML)    | author              | `kbi`                    |
| Slice                 | `<catalog>/index/<domain>.md` | `kbi` (generated)   | consumers, humans        |

`kbi` indexes only `*.kb.md` cards; it ignores `kb.yml` and `cards.yml` (those are
author-side).

## 1. The Card — `<name>.kb.md`

A distilled, self-contained unit of knowledge: YAML frontmatter plus a Markdown
body. Lives in the `.kb/` directory beside its source.

### 1.1 Filename

- One card from a file/dir: `<source-stem>.kb.md` (e.g. `Plan.kb.md`); a
  whole-directory card may use the directory basename.
- Multiple cards from one file (section splits): `<source-stem>.<section-slug>.kb.md`
  (e.g. `report.architecture.kb.md`), each with the same `source` and a distinct
  `scope`.

### 1.2 Frontmatter fields

Required:

- `id` — stable UUID; the immortal identity. Never changes, never reused.
  Everything (`builds_on`, links) ultimately resolves to it.
- `title` — human-readable title (also the card's H1).
- `source` — path **relative to the card's `.kb/` directory** to the origin: a
  file (`../Plan.md`), a directory (`..`), a URL, or a list of these. The
  "dig deeper" link.
- `domain` — the subject domain; routes the card to a slice and selects the
  area profile.
- `tags` — bottom-up content tags (kebab-case). Reused across cards to form the
  content-centered index.

Optional:

- `slug` — readable alias for the card (kebab-case). Used in `builds_on` and link
  targets for readability; resolves to `id` underneath.
- `builds_on` — list of card ids/slugs this card depends on (prerequisite edges).
- `defines` — terms this card is the canonical home for (feeds the glossary and
  `[[term]]` link resolution).
- `related` — lateral (non-prerequisite) links. (Reserved; use sparingly.)
- `created` / `updated` — ISO dates. `updated` vs the source date flags staleness.
- `source_hash` — `sha256:<hex>`; change-detection for regeneration.
- `meta` — open map for domain-specific keys (e.g. `scripture`, `section`,
  `cve`), so the core schema stays universal.

### 1.3 Body

- `# <title>` — H1 (one per file).
- `> essence` — a one-sentence blockquote; the mandatory hook hoisted into slices.
  May span lines (joined).
- `## Core Concepts` — distilled nested bullets (tabs for nesting).
- `## Key Quotes` — present **only** for quote-enabled profiles (see §2.2);
  exact quotes grouped under short thematic sub-bullets.

### 1.4 Inline links

- Stored form: `[[target|surface text]]` where `target` is a card `slug` (or
  `id`); the surface text is what reads in prose.
- Authoring shorthand `[[term]]` resolves via the term index (a card's `defines`)
  to the defining card. Links resolve to the whole card (no sub-anchors in v1).

### 1.5 Example

```markdown
---
id: ac806768-6b8d-4c4c-bd22-f8a5a831f7ff
slug: fall-2025-l07-when-god-interrupts
title: When God Interrupts Your Life
source: ../Plan.md
domain: spiritual
tags: [faith, obedience, interruption-as-invitation]
defines: [interruption-as-invitation]
created: 2026-06-07
updated: 2026-06-07
meta:
  scripture: ["Hebrews 11:8-19"]
---

# When God Interrupts Your Life

> What looks like an interruption is God's invitation into His greater purposes.

## Core Concepts

- faith moves forward without all the answers
	- obedience before understanding

## Key Quotes

- on faith
	- "What we call interruptions, God calls invitations."
```

## 2. Area Config — `kb.yml`

One per knowledge-base area, at `<area>/.kb/kb.yml`. It declares policy for the
whole subtree beneath it.

**Inheritance:** the effective config for a directory is resolved by walking up
to the nearest ancestor `.kb/kb.yml`, merged **per key, nearest-ancestor-wins**.
A sub-level `kb.yml` may override individual keys (e.g. only `card_split`) and
inherit the rest.

### 2.1 Fields

Required:

- `domain` — the area's domain; also its catalog key and subscription target.
  Unique across the catalog (one area per domain). May be broad (`technical`) or
  granular (`sdv-research`).

Optional:

- `title` / `description` — friendly name / one-line summary (catalog + slice
  header).
- `profile` — named distill profile (see §2.2). Defaults from `domain`.
- `distill_level` (1–3) / `quotes` (bool) — fine overrides of the profile.
- `seed_tags` — ~10–15 anchor tags new cards reconcile against (keeps the
  vocabulary convergent).
- `meta_fields` — domain-specific frontmatter keys cards should carry (e.g.
  `scripture`), so authoring extracts them into `meta`.
- `card_unit` — granularity anchor: `repo | directory | file | section` (see §4).
- `card_split` — whether to split an over-dense unit: `auto | never` (see §4).
- `card_density` — how deep to split: `coarse | normal | fine | exhaustive`,
  default `normal` (see §4).
- `draws_on` — list of upstream domains this area subscribes to (drives consumer
  wiring; rendered as a cross-domain edge).

### 2.2 Profiles and resolution

A profile is "how to distill" = distill level + quotes on/off. Built-in profiles:

| Profile      | distill_level | quotes | Typical domains         |
|--------------|---------------|--------|-------------------------|
| `standard`   | 2             | false  | technical, finance, sdv |
| `reflective` | 2             | true   | spiritual, personal-dev |
| `deep`       | 3             | true   | high-value material     |

Domain defaults: `spiritual`, `personal-dev` → `reflective`; all others →
`standard`. Resolution precedence (highest first): explicit `distill_level` /
`quotes` → named `profile` → domain default → `standard`.

### 2.3 Example

```yaml
domain: spiritual
title: Bible Studies for Life (BSFL)
profile: reflective
seed_tags: [faith, grace, discipleship, surrender, obedience, suffering]
meta_fields: [scripture]
```

## 3. Segmentation Manifest — `cards.yml`

One per directory, at `<dir>/.kb/cards.yml`. It is the **record** of how that
directory's sources were divided into cards (the reviewed boundary decisions),
covering every source in the directory — including multiple cards carved from one
file. It is *not* the card content (that is regenerated). `/kb-card` writes and
reconciles it; `kbi` ignores it.

### 3.1 Top-level fields

- `version` — manifest format version (currently `1`).
- `updated` — ISO date of last reconcile.
- `density` — the directory's effective depth (`coarse|normal|fine|exhaustive`).
- `density_overrides` — optional list of per-`(source, section)` depth directives
  (non-uniform depth). Each entry: `source`, `section`, `density`.
- `cards` — the list of card entries.

### 3.2 Card entry fields

- `slug` — the card's slug.
- `id` — the card's stable UUID.
- `file` — the card filename within `.kb/`.
- `source` — source path relative to `.kb/` (same as the card's `source`).
- `scope` — for section/sub-file cards: `section` (heading identity) and
  `signature` (a short semantic fingerprint — *not* page numbers, so the boundary
  can be re-validated after edits). Omit for whole-file/whole-directory cards.
- `title` — the card title.
- `locked` — `true` if the boundary is human-ratified. A locked boundary is never
  changed *silently*, but is auto-escalated to review when content drift
  invalidates it. It is not immutable.
- `source_hash` — `sha256:<hex>` of the source at last author/refresh; drives
  drift detection.

### 3.3 Reconcile semantics

On a re-run, `/kb-card` diffs the sources against `cards.yml` and classifies each
card (see §4.4). Boundaries are sticky; content is regenerated. Decisions are
refined, never redone.

### 3.4 Example

```yaml
version: 1
updated: 2026-06-07
density: fine
density_overrides:
  - source: ../reports/foo.pdf
    section: "Architecture"
    density: fine
cards:
  - slug: sdv-arch-overview
    id: 7f3a0000-0000-0000-0000-000000000000
    file: foo.architecture.kb.md
    source: ../reports/foo.pdf
    scope:
      section: "Architecture"
      signature: "VMkernel, VMFS, cluster file system"
    title: 'Foo: Architecture'
    locked: true
    source_hash: sha256:8aae357d...
```

## 4. The `/kb-card` Command (author-side)

Creates/updates cards and reconciles `cards.yml`. Granularity is **adaptive-first**
(the command proposes the cut) with `kb.yml` overrides and manual review. It does
**not** run `kbi`.

### 4.1 Usage

```
/kb-card [source] [-r] [-plan] [-resegment] [-update]
         [-density coarse|normal|fine|exhaustive] [-cards <N>]
         [-domain <d>] [-level 1|2|3] [-quotes | -no-quotes]
```

- `source` — file, directory, or omitted (current directory).
- `-r` — recurse: author a card per unit across the tree.
- `-plan` — propose/update `cards.yml` and **stop before authoring** — the
  review/adjustment gate.
- `-resegment` — discard a source's existing boundaries and re-propose fresh.
- `-update` — refresh content of existing cards whose source drifted.
- `-density` — depth of the split (overrides `kb.yml card_density`).
- `-cards <N>` — a **maximum** card count (a ceiling, **never a quota**):
  partitioning stops at the finest meaningful boundary and never invents or
  fragments topics to reach N.
- `-domain` / `-level` / `-quotes` / `-no-quotes` — override domain / profile.

### 4.2 Granularity model (three dials)

- `card_unit` — *where* cuts can fall: `repo | directory | file | section`.
- `card_split` — *whether* to split a unit: `auto | never`.
- `card_density` — *how deep* to split: `coarse | normal | fine | exhaustive`. For
  one report this is roughly the difference between ~2 / ~4 / ~8 / ~16 cards
  (themes → section groups → sections → subsections). Density expresses
  willingness to spend cards; **cohesion is the floor** — it cannot manufacture
  distinctions the content lacks. Depth may be non-uniform via `density_overrides`.

All three are *optional overrides* of the adaptive proposal; omit them to let
`/kb-card` choose.

### 4.3 Pipeline

1. Resolve scope + area config (`kb.yml`) and the effective profile/density.
2. **Segment:** propose boundaries (adaptive, honoring overrides), reconcile
   against `cards.yml`, present the delta for review, write `cards.yml`. (`-plan`
   stops here.)
3. **Author/refresh:** distill each new/refreshed/re-segmented scope per the
   profile; reconcile tags; extract `meta`; assemble frontmatter; linkify known
   terms; write the card.
4. Retire orphans; report. (Does not run `kbi`.)

### 4.4 Reconcile outcomes

On re-run, each existing card is classified:

- **keep** — `source_hash` unchanged.
- **refresh** — source changed but the boundary still resolves (validated
  semantically against `scope.section`/`signature`) → regenerate content, keep
  the boundary.
- **re-segment** — source changed and the boundary no longer resolves → break the
  lock and escalate that source to review.
- **orphan** — the source is gone → retire the card.
- **new** — an uncarded section/source appeared → propose a new card.

## 5. The `kbi` Indexer and Catalog Config (catalog-side)

`kbi` discovers files, computes a render-independent index model, and emits it
through a renderer. Run it with a config:

```
python3 kbi.py --config <config.yml>
```

### 5.1 Config schema

- `directories.include` — list of root paths to scan (the registry of indexed
  repos). `directories.exclude` — glob patterns to prune.
- `keywords.files` — optional keyword files (mind-map renderer only).
- `output.file` — for `freeplane`, the `.mm` output file; for `markdown`, the
  output **directory** for slices.
- `output.format` — `freeplane` (default) or `markdown`.
- `file_types` — map of enabled types; each has `extensions` and `handler`. **An
  explicit `file_types` replaces the defaults** (it does not merge), so the set of
  enabled types defines the index scope.

### 5.2 Scoping via `file_types`

- **Card-only (catalog):** enable only `card` (`extensions: [".kb.md"]`,
  `handler: CardHandler`) → indexes only distilled cards.
- **Deep (within-repo):** enable `card` + `markdown` + `freeplane` → indexes full
  content; cards are still parsed card-aware.
- **Precedence:** when more than one type matches, the **longest matching
  extension wins**, so `.kb.md` is always handled by `CardHandler` over `.md`.

### 5.3 Renderers

- `freeplane` — a Freeplane `.mm` mind map (the human navigation view). Branches:
  File System, Keyword, Tag, Word.
- `markdown` — per-domain **slices**: one `<domain>.md` per domain plus an
  `INDEX.md` overview, written into the output directory. Each slice lists, per
  card: title, essence, tags, `builds_on` (resolved to titles), `defines`, card
  path, and source; plus a domain-local tag index and a glossary (defined term →
  card).

### 5.4 Catalog config example

```yaml
directories:
  include:
    - "/home/jon/dev/BSFL"
    - "/home/jon/dev/research/SDV-research"
  exclude: ["**/.git/**", "**/__pycache__/**"]
keywords:
  files: []
output:
  file: "/home/jon/dev/kb/index"
  format: "markdown"
file_types:
  card:
    extensions: [".kb.md"]
    handler: "CardHandler"
```

## 6. Consumer Subscription Model

Consumers (council members, projects, ad-hoc sessions) **subscribe** to a domain
by referencing its slice — they pull; the KB never pushes.

- **Slice location (convention):** `~/dev/kb/index/<domain>.md`.
- **Shared protocol once:** the generic retrieval protocol (scan the slice → open
  1–3 cards → follow `source:` only for depth) lives in the council `CLAUDE.md`.
- **Per-member subscription:** each member's `CLAUDE.md` declares only *which*
  slice(s) it subscribes to. Because `CLAUDE.md` loads up the directory tree, a
  member-only session inherits the shared protocol automatically.
- **Project subscription:** a project declares `draws_on: [<domain>]` in its
  `kb.yml`, or references the slice directly in its `CLAUDE.md`.
