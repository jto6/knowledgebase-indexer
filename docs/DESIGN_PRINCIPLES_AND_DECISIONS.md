# Knowledge Base System — Design Principles and Decisions

Status: Draft / in active design. Started 2026-06-07.

This document captures the architecture, the principles behind it, and the key
decisions (with rationale) for a personal knowledge base system that is useful
both to a human (Jon) and to Claude Code.

It sits *above* `kbi_PRD.md`. The PRD specifies the indexer engine (the thing
that reads many files and emits navigation views); this document specifies the
larger system the indexer serves, and therefore drives future PRD extensions
(see "Implications for kbi").

BSFL (`/home/jon/dev/BSFL`) is the **first instance / proving ground**, not the
target. The system is intended to generalize across spiritual, personal-
development, financial, technical, and any other research domains.

## 1. Problem and Goals

The knowledge lives as large collections of source material (PDFs, docs, notes)
scattered across many directories. Two consumers need fast, high-signal access
to its essence:

- **Human review (purpose #1).** The mind holds a limited working set. Jon wants
  a distilled, periodically-reviewable summary of the key concepts per source,
  usable as an index, with a link back to the full material to dig deeper.
- **Claude / agent retrieval (purpose #2).** Claude Code — especially the
  advisory council members (e.g. Rev. Samuel Grace, the pastor, over BSFL) —
  needs to find and pull relevant knowledge for the current context, with low
  token cost and fast search.

## 2. Core Architecture — Three Layers

The recurring "centralized vs. distributed" tension dissolves once three layers
that were being conflated are separated:

| Layer          | Artifact                                             | Lives where                     | Maintained how                 |
|----------------|------------------------------------------------------|---------------------------------|--------------------------------|
| **1. Card**    | One distillate per source item (lesson, paper, note) | Distributed — beside its source | Authored (via distill tooling) |
| **2. Shelf**   | Per-consumer index of cards (per area, per domain)   | Anywhere it is consumed         | Generated (a view)             |
| **3. Catalog** | Cross-domain navigational map + tag/term indexes     | Centralized (in kbi)            | Generated (by kbi)             |

The unifying rule: **the source of truth is always distributed and co-located;
everything centralized is *generated* from it.** A hand-maintained central
database is the thing to avoid — it duplicates content and goes stale silently.
A *derived* central index can never be wrong for long, because it is rebuilt.

## 3. Design Principles

These are the load-bearing rules. Decisions below are applications of them.

- **P1 — Distributed truth, centralized derived views.** Authored content (cards)
  is co-located with its source. Anything central is generated and rebuildable,
  never a second source of truth.
- **P2 — Generated artifacts are free to live anywhere, in any number.** A shelf
  is a *view* (a query result), so it may be materialized wherever a consumer
  wants it, in multiple copies, without duplication risk.
- **P3 — Synthesis before retrieval.** A card is a lossy, judgment-laden
  *distillation* (core principles + best quotes), not raw text. This is the one
  thing no search engine provides and the only thing that serves purpose #1.
  Retrieval (search) is recall; it sits on top of synthesis, never replaces it.
- **P4 — Bottom-up vocabularies, groomed not authored.** Tags and terms are born
  on cards, reconciled against what already exists at authoring time, and
  periodically consolidated by tooling that *proposes* merges for approval.
  Curation effort scales with vocabulary *drift*, not corpus *size*.
- **P5 — Plain-text durability.** Cards and indexes are markdown: greppable,
  diffable, git-versioned, portable, and they survive tooling changes. Opaque
  infrastructure (e.g. a vector store) is added only when measured, and never as
  the foundation.
- **P6 — Earn your place (anti-clutter).** Every schema field and every artifact
  must be consumed by a renderer, a tool, or a human follow-link. Unused
  structure is removed.
- **P7 — Consumers pull; the KB never pushes.** A consumer (council member,
  project, ad-hoc session) subscribes by *referencing* a domain's index. This is
  one uniform mechanism for all consumers.
- **P8 — Readable surface over a stable anchor.** Identity is a stable opaque
  anchor; humans interact through readable aliases and surface text. Renames are
  a tooling operation, not a manual hazard.
- **P9 — One model, many renderers.** The indexer computes one index model and
  renders it multiple ways (human mind map, Claude markdown, per-domain slices).

## 4. Key Decisions

Each decision records the choice and why; supersessions are noted in the addenda.

- **D1 — Three-layer model (card / shelf / catalog).** See §2. Resolves the
  centralized-vs-distributed question by layer rather than globally. (P1, P2)
- **D2 — Cards live in a per-directory `.kb/` folder.** Each source directory
  gets its own hidden `.kb/` holding that item's card(s). Chosen over both a
  visible co-located file (clutter) and a single top-level mirrored tree (a
  parallel structure to keep in sync). The card never separates from its source,
  the link-back is a relative path, and there is no second tree to maintain;
  when a folder moves, its `.kb/` rides along. (P1, P6)
- **D3 — Card identity is a stable UUID, with an optional human slug alias.**
  `id` is an immortal UUID (never changes, never reused) that everything resolves
  to. `slug` is a mutable, readable alias for the places UUIDs hurt readability
  (frontmatter cross-refs). Inline links carry surface text — `[[target|surface
  text]]` — so prose stays readable regardless of the target form. A `rename`
  tool updates references; stale slugs may remain as redirects. (P8)
- **D4 — Two link tiers.** `builds_on` (frontmatter, card → card) expresses coarse
  prerequisite/foundation structure. Inline `[[term]]` links express fine-grained
  Wikipedia-style "defined over there" references, resolved via a term index
  (term → canonical defining card). Deep sub-anchor links (`[[id#term]]`) are
  deferred. (P4, P8)
- **D5 — Tags and terms are bottom-up and groomed.** No top-down master
  vocabulary is authored. Authoring reconciles against existing tags/terms
  (reuse > invent); a `consolidate` tool aggregates across all cards and proposes
  synonym/near-duplicate merges for approval. Each domain is *seeded* with ~10–15
  anchor tags so early cards have something to reconcile against. (P4)
- **D6 — Profiles separate "what to distill" from "how."** A profile = distill
  level + quotes on/off (+ which seed vocabulary). Many domains map to one
  profile (e.g. `spiritual` and `personal-dev` both use the quotes profile;
  `technical` uses no quotes). (P6)
- **D7 — Domains are declared per-area, not decreed centrally.** Each area
  declares its `domain` in its `.kb/kb.yml`; the union of declarations *is* the
  domain vocabulary. Domains are few and slow-changing, so bottom-up declaration
  suffices. `domain → profile` is many-to-one; `domain → consumer` is
  many-to-many. (P4, P7)
- **D8 — Two config tiers.** The **central kbi config** declares *which roots are
  in the catalog* (the registry of knowledge bases / index scope). The
  **per-area `.kb/kb.yml`** declares that area's `domain`, `profile`, `seed_tags`,
  and `draws_on`. (P1, P7)
- **D9 — Uniform subscription model.** Consumers pull from a domain's index slice
  published at a predictable path (e.g. `~/dev/kb/index/<domain>.md`). Modes:
  persistent (a project's `CLAUDE.md` references the slice + a retrieval
  protocol), declared (an area's `kb.yml` `draws_on:` lists upstream domains, and
  tooling generates the `CLAUDE.md` stanza), and ad-hoc (an in-session pointer,
  or a future `/kb-use <domain>` command). Council members are just one kind of
  consumer. (P7)
- **D10 — Retrieval default is native grep/read over curated cards + slices.**
  Over a distilled, well-tagged card set, Claude Code's native lexical retrieval
  is high-signal enough to be the default. No vector store unless a recall gap is
  measured; if added, it embeds the *cards* (and optionally sources), runs
  locally, and sits on top of the card layer. (P3, P5) — see Addendum A.
- **D11 — `/kb-import` is retired.** Built around old Claude Code limits, it was
  superseded by cards + native source reading; its one residual role (archiving
  volatile remote URLs) is now fulfilled by `/kb-card`'s URL capture (D15). The
  command has been removed. (P6) — see Addenda D and G.
- **D12 — Catalog scope is the set of enabled `file_types`; a card is a file
  type.** kbi indexes a file only if its extension belongs to an *enabled* file
  type, and `*.kb.md` cards are their own type (`CardHandler`, keyed on the
  compound `.kb.md` extension and winning precedence over `.md`). So one engine
  serves two profiles by configuration alone: a **card-only catalog** (enable
  only `card` → distilled, cross-repo) and a **deep within-repo index** (enable
  `card` + `markdown` + … → full content, local output). An explicit `file_types`
  **replaces** the defaults rather than merging, so scope can actually be
  narrowed. (P9, D2) — see Addendum F. *(Implemented in increment A.)*
- **D13 — Central catalog home is `~/dev/kb/`; slices live at
  `~/dev/kb/index/<domain>.md`.** kbi's markdown renderer writes per-domain slices
  to this predictable path so any consumer can subscribe. The retrieval protocol
  is defined once in the council `CLAUDE.md`; each council member's `CLAUDE.md`
  declares only which slice(s) it subscribes to — the protocol is generic, the
  subscription is per-member. Because Claude Code loads `CLAUDE.md` up the
  directory tree, a member-only session still inherits the shared protocol.
  (P2, P7, D9) *(Implemented when wiring the pastor; resolves the §8 slice-home
  question.)*
- **D14 — Card granularity is adaptive-first with declarative override, and the
  boundary decisions are persisted per directory in `cards.yml`.** A card should
  be one cohesive, self-contained, bounded topic — the unit at which distillation
  stays faithful and retrieval stays precise. Granularity is a *cut* across the
  source hierarchy (repo → directory → file → section); `/kb-card` *proposes* the
  cut by content analysis, and the optional `card_unit` / `card_split` /
  `card_density` keys in `kb.yml` (inherited per subtree) override the proposal
  where the author wants control, including how *deep* to partition (a `-cards N`
  ceiling never invents topics to fill a quota), with non-uniform per-section depth
  recorded in `cards.yml`. Reviewed boundaries are recorded in a per-directory `.kb/cards.yml`
  manifest (the realized record, not a forward plan); re-runs **reconcile**
  against it — refreshing drifted content, escalating boundaries that no longer
  resolve, and flagging orphans — so decisions are refined, never redone.
  (P3, P4) — see §6.4.
- **D15 — Remote/URL sources are handled by capturing a local text artifact that
  becomes the *operational* source of truth.** A card cannot be co-located with a
  remote source (a YouTube URL has no local home), so `/kb-card <url>` fetches a
  **transcript** (via `/distill`), writes it as a *visible* local source document
  — the directory's content, browsable and re-segmentable, the same role a
  lesson's `Plan.md` plays — and distills the card from it. The card's `source`
  lists the **URL first** (canonical "dig deeper") and the local capture second
  (the analyzable basis for `-resegment` / drift). Two tiers of truth: the local
  capture is the *operational* source of truth (what every automated step reads);
  the URL is the *canonical* original (human/Claude fallback). Fidelity is
  recorded in `meta.capture` (e.g. `transcript`). Visual/multimodal capture
  (`transcript+visual`) is **opt-in and deferred** — expensive, requires the
  video, and only enriches the same local text artifact, so it needs no
  architectural change; a cheap transcript-reference heuristic warns when a
  transcript-only capture is likely lossy. (P1, P3, P5) — see Addendum G; this
  also absorbs the residual `/kb-import` role (D11, Addendum D).

## 5. Card Schema (current)

Frontmatter:

- `id` (required) — stable UUID; the immortal handle everything resolves to.
- `slug` (optional, recommended) — readable alias for cross-refs and links.
- `title` (required) — human label.
- `source` (required) — file, directory, URL, or a list of these; defaults to
  `..` (the directory the `.kb/` sits in) when the card summarizes the whole
  folder. The "dig deeper" follow-link. For a remote source, list the URL first
  (canonical) and the local capture second (the analyzable basis) — see D15.
- `domain` (required) — routes to a consumer slice and selects the profile.
- `tags` (required) — bottom-up, reconciled content taxonomy.
- `builds_on` (optional) — list of card ids/slugs (prerequisite links).
- `defines` (optional) — terms this card is the canonical home for (feeds the
  term index / glossary).
- `related` (optional, deferred) — lateral links; omitted until a real need.
- `created` / `updated` (optional) — `updated` vs source date flags staleness.
- `source_hash` (optional) — change detection for regeneration (manifest hash for
  directory sources).
- `meta` (optional) — open map for domain-specific keys (e.g. `scripture`,
  `ticker`, `cve`; and `capture` for remote sources — the capture method/fidelity,
  see D15) so the core schema stays universal.

Body:

- `# Title` (H1) — headers matter because the indexer builds hierarchy from them.
- `> essence` — a one-sentence blockquote; the mandatory hook hoisted into shelves
  and map nodes.
- `## Core Concepts` — distilled nested bullets; inline `[[term]]` links allowed.
- `## Key Quotes` — present only for quote-enabled profiles (spiritual,
  personal-dev); absent for technical.

A **glossary card** is not a special type — it is simply a card whose `defines`
is populated and whose body defines that one concept.

## 6. Area Configuration (`kb.yml`)

One `kb.yml` lives at each knowledge-base area root, at `<area>/.kb/kb.yml`. It
applies to the **whole subtree** beneath it; the effective config for any card is
the nearest `kb.yml` found walking up from the card. Normally there is exactly
one per area (e.g. `/home/jon/dev/BSFL/.kb/kb.yml`), but a sub-level may override
if ever needed. It is deliberately minimal (P6): only `domain` is required, and
everything else is defaulted or omitted.

### 6.1 Fields

- `domain` (required, string) — the area's domain. Also serves as the area's key
  in the catalog and the target name for subscriptions, so it must be unique
  across the catalog (one area per domain for now). May be broad (`technical`) or
  granular (`sdv-research`) — granularity is the author's choice (P4, D7).
- `title` (optional, string) — friendly area name for the catalog node and the
  per-domain slice header. Defaults to the directory name.
- `description` (optional, string) — one-line area summary for the slice header.
- `profile` (optional, string) — named distill profile. Defaults from `domain`
  (see 6.2). Specify only to override the domain's default.
- `distill_level` (optional, 1–3) — advanced override of the resolved profile's
  level. Rarely needed.
- `quotes` (optional, bool) — advanced override of the resolved profile's quotes
  setting. Rarely needed.
- `seed_tags` (optional, list) — ~10–15 anchor tags that early cards reconcile
  against, so the bottom-up vocabulary converges instead of sprawling (P4, D5).
- `meta_fields` (optional, list) — domain-specific frontmatter keys cards in this
  area should carry (e.g. `scripture`), so the authoring step knows to extract
  them into the card's `meta` map.
- `draws_on` (optional, list of domains) — upstream domains this area subscribes
  to. Drives the subscription wiring (D9): tooling can generate this area's
  `CLAUDE.md` KB-access stanza, and the catalog renders the dependency as a
  cross-domain edge.
- `card_unit` (optional: `repo` | `directory` | `file` | `section`) — overrides
  the adaptive card-granularity choice for this subtree (see §6.4). Omit to let
  `/kb-card` choose adaptively.
- `card_split` (optional: `auto` | `never`) — whether `/kb-card` may split an
  over-dense unit into finer section cards (see §6.4). Omit to let `/kb-card`
  decide adaptively.
- `card_density` (optional: `coarse` | `normal` | `fine` | `exhaustive`, default
  `normal`) — how *deep* a split goes: how far down the source's section/subsection
  hierarchy the cuts fall (see §6.4).

### 6.2 Profiles and resolution

A profile is "how to distill" = a distill level + quotes on/off (D6). Profiles
are engine knowledge (a small, slow-changing table), not a hand-maintained
content vocabulary, so their definitions live centrally in kbi. Built-in defaults:

| Profile      | distill_level | quotes | Typical domains         |
|--------------|---------------|--------|-------------------------|
| `standard`   | 2             | false  | technical, finance, sdv |
| `reflective` | 2             | true   | spiritual, personal-dev |
| `deep`       | 3             | true   | high-value material     |

Domain → default profile: `spiritual` and `personal-dev` → `reflective`; all
other / unknown domains → `standard`. Resolution precedence for the effective
distill behavior:

1. explicit `distill_level` / `quotes` in `kb.yml` (advanced override), else
2. the named `profile` in `kb.yml`, else
3. the domain's default profile, else
4. `standard`.

### 6.3 Examples

BSFL (the spiritual proving ground), at `/home/jon/dev/BSFL/.kb/kb.yml`:

```yaml
domain: spiritual
title: Bible Studies for Life
# profile: reflective        # default for spiritual; shown for clarity only
seed_tags:
  - discipleship
  - grace
  - faith
  - prayer
  - forgiveness
  - identity-in-christ
  - the-holy-spirit
  - surrender
  - obedience
  - suffering
  - community
  - witness
meta_fields:
  - scripture
```

A technical area that builds on another, at
`/home/jon/dev/SDV-SRD/.kb/kb.yml`:

```yaml
domain: sdv-srd
title: SDV System Requirements
draws_on:
  - sdv-research
seed_tags:
  - requirements
  - architecture
  - safety
  - autosar
  - middleware
```

The upstream area it subscribes to, at
`/home/jon/dev/research/SDV-research/.kb/kb.yml`:

```yaml
domain: sdv-research
title: SDV Research
seed_tags:
  - architecture
  - middleware
  - safety
  - virtualization
  - standards
```

Note that per-domain slice *output* paths (e.g. `~/dev/kb/index/<domain>.md`) are
a catalog/engine concern declared in the central kbi config, not in `kb.yml`,
keeping the area config focused on what the area *is* rather than where the
catalog writes.

### 6.4 Card Granularity and the `cards.yml` Manifest

**Sizing principle.** One card = one cohesive, self-contained, bounded topic — the
unit at which distillation stays faithful (acceptable information loss) and
retrieval stays precise. Too coarse loses detail (one card for a directory of
distinct reports); too fine fragments.

**Granularity is a cut across the source hierarchy** (`repo → directory → file →
section`). How big a card is = how deep the cut goes, and the cut may go deeper
where content is denser. Two controls set it:

- *Adaptive proposal (default).* `/kb-card` content-analyzes the sources and
  proposes the cut — detecting natural seams (sections, distinct files) and the
  "one thing vs. many things" distinction (a BSFL lesson folder is variants of one
  lesson → one card; a `reports/` folder is many distinct documents → one card
  each, splitting a dense report into per-section cards).
- *Declarative override.* `card_unit` / `card_split` in `kb.yml` (inherited per
  subtree, nearest-ancestor-wins) override the adaptive choice. This expresses
  heterogeneity directly: e.g. `sdv-research/.kb/kb.yml` → `card_unit: file`, with
  `sdv-research/reports/.kb/kb.yml` → `card_split: auto`.
- *Depth (density).* `card_density` (`coarse|normal|fine|exhaustive`) controls how
  far down the hierarchy the cuts go — for one report, the difference between ~2,
  ~4, ~8, or ~16 cards (themes → section groups → sections → subsections). Set it
  as a `kb.yml` default, per-run via `/kb-card -density fine`, or cap the count
  with `/kb-card -cards N`. **`-cards N` is a ceiling, not a quota**: partitioning
  stops at the finest *meaningful* boundaries and never invents or fragments topics
  to reach N (if a depth would exceed N, the least-distinct boundaries are merged).
  Density expresses willingness to spend cards; cohesion is still the floor — it
  cannot manufacture distinctions the content lacks.

Depth can be **non-uniform**: a `density_overrides` entry in `cards.yml` raises (or
lowers) the density for one `(source, section)` scope while the rest of the
directory keeps the global `density`. The override is a durable *directive* (intent),
distinct from the realized card list (result): on re-run the proposer applies the
override to existing *and new* content in that scope, and the global density
everywhere else — so "go deeper here" survives and propagates correctly.

Adaptive is strong at finding seams but weak at marginal cohesion calls and at
cross-run consistency, so it *proposes*; the human *reviews* (initially); and the
decision is *persisted* — which is what neutralizes the consistency weakness.

**The `cards.yml` manifest.** Each directory's `.kb/cards.yml` records the reviewed
result — how that directory's sources are divided into cards. It is the record of
boundary *decisions*, not the card content (which is regenerated). One manifest per
directory, covering every source in it, including multiple cards carved from a
single file:

```yaml
# .kb/cards.yml — reviewed segmentation manifest for this directory.
version: 1
updated: 2026-06-07
density: normal                  # effective depth for this directory (from kb.yml/-run)
density_overrides:               # optional: non-uniform depth, by (source, section)
  - source: ../reports/foo.pdf
    section: "Architecture"
    density: fine
cards:
  - slug: sdv-arch-overview
    id: 7f3a...                  # stable card id
    file: foo.architecture.kb.md
    source: ../reports/foo.pdf   # relative to this .kb/
    scope:                       # omit for whole-file / whole-directory cards
      section: "Architecture"
      signature: "<short topic fingerprint>"   # semantic anchor, not page numbers
    title: SDV Architecture Overview
    locked: true                 # human-ratified boundary
    source_hash: sha256:...
```

`kb.yml` holds area *policy* (inherited); `cards.yml` holds the *realized*
boundaries for one directory (local, concrete).

**Boundaries vs. content.** Boundaries are sticky (in `cards.yml`, human-
controlled); content is regenerated from source. Updating a source refreshes the
card's content but preserves the boundary.

**Reconcile on re-run (refine, don't redo).** `/kb-card -r` re-analyzes, diffs
against `cards.yml`, and surfaces only the delta:

- source unchanged (hash match) → keep the card as-is;
- source changed, boundary still resolves (validated *semantically* against the
  card's section/signature, not by page number) → refresh content, keep boundary;
- source changed, boundary no longer resolves → break the lock and escalate that
  source to re-segmentation review (`locked` protects against *silent* change, not
  against escalation when content drift invalidates the boundary);
- source gone → flag the card as an orphan for retire/delete.

A manual `/kb-card -resegment <source>` forces a fresh segmentation of one source
when the author already knows the content changed dramatically. The invariant:
decisions are honored while they remain meaningful; when the ground shifts under a
specific source, only that source is re-decided — never the whole tree, never
silently. The `scope` anchor is therefore semantic (section identity + a topic
signature) with page ranges as a derived hint, so "is this boundary still valid?"
is reliably answerable.

`cards.yml` is author-side; kbi indexes only `*.kb.md` cards and ignores it.

## 7. Implications for kbi (future PRD extensions)

The decisions lean harder on the indexer than today's implementation. All are
*additive* to the existing one-model architecture (P9).

Done (increment A):

- Discover cards inside `.kb/` — kbi already uses `os.walk`, which descends into
  hidden directories, so the feared dot-directory glob change was unnecessary.
- Parse **YAML frontmatter `tags`** — already supported by the markdown handler;
  the `CardHandler` now labels them by the card **title** instead of the filename.
- `CardHandler` + card scoping via enabled `file_types` (see D12).

Done (increment B):

- **Markdown renderer** — per-domain slices at `~/dev/kb/index/<domain>.md`, each
  listing per-card title/essence/tags/source, with `builds_on` resolved to
  titles, a content-clustered tag index, and a glossary (defined term → card).
- Consumer subscription wired (the pastor) via the shared protocol (D13).

Pending (increment C and beyond):

- Add a **`consolidate`** mode: aggregate tags/terms, propose synonym merges.
- Build a **term index** (term → canonical defining card) for `[[term]]` linking.
- Render **`builds_on` / `draws_on`** as cross-area/cross-domain edges in the map.
- Provide a **`rename`** operation (id/slug rename + reference update).

## 8. Open Questions

- Details of the `rename` tooling and slug-redirect handling.
- When (if) to introduce deep sub-anchor links `[[id#term]]`.

## Addenda — Considerations

These capture the deeper deliberations behind the decisions, for future readers
who want the "why" and the roads not taken.

### Addendum A — Structured metadata vs. general semantic search

Question: instead of explicit cards/metadata, should effort go into a general
LLM/vector search capability (e.g. Vectara) over all the raw content?

Conclusion: **they are complementary, not a fork** — the card layer is the ideal
*substrate* for semantic search, not an alternative to it. Reasoning:

- A card performs **synthesis** (distillation to core principles + best quotes).
  A vector index performs **none** — it returns raw chunks. Purpose #1 (periodic
  human review) is served *only* by the card; you cannot review a vector store.
- The corpus has heavy duplication (multiple versions per lesson) and boilerplate.
  Raw RAG has no notion of *canonical*; it returns near-duplicate, low-signal
  chunks and burns the context window. The card is the one curated representation.
- Vectors give **similarity**, never **relationship**. `builds_on`, definitions,
  and the navigational map are graph queries semantic search cannot answer.
- Vectors uniquely win on **recall** (the untagged long tail) and **zero authoring
  cost**, which is real and valuable.

Recommended sequencing: (1) build the card layer; (2) for Claude retrieval, start
with native grep/read over curated cards + generated slices — likely sufficient,
zero infra; (3) add semantic search only on a *measured* recall gap, embedding the
*cards* (and optionally sources), running **locally** (pgvector / LanceDB /
sqlite-vec) rather than a third-party SaaS, given the sensitivity of personal
spiritual and financial content. Heuristic: *cards answer "what do I know and
what's the essence?"; vectors answer "where, in everything, is this mentioned?"* —
synthesis is needed first and cannot be outsourced to an embedding model.

### Addendum B — Centralized vs. distributed storage

Resolved by the three-layer model (D1): distributed authored cards, centralized
*generated* catalog. The shelf, being generated, is location-free (P2) and is
materialized per consumer — which is the same thing as the per-domain slice in
the subscription model (D9).

### Addendum C — UUID vs. readable-slug identity

Initial position favored readable slugs (to preserve `[[wiki-link]]` ergonomics).
Superseded by D3: because `[[target|surface text]]` separates the link *target*
from the displayed *text*, and a term index resolves surface → card regardless,
the target may be an opaque UUID without harming prose readability. UUID gives
mechanical stability and collision-freedom; the optional `slug` restores
readability for frontmatter cross-refs. Best of both: UUID anchor + slug surface.

### Addendum D — `/kb-import` relevance

`/kb-import` (and its `.kbmap`) was built around earlier Claude Code limitations
(no native PDF/DOCX reading, weaker WebFetch). Cards + native source reading now
cover almost all of its use. It should be removed or reduced to a single narrow
job — archiving volatile remote URLs that may change or disappear (the one thing a
`source:` link cannot guarantee). The only salvageable idea is `source_hash` for
staleness detection, now folded into the card schema. Now **retired**: that
residual archiving role is fulfilled by `/kb-card`'s URL capture (D15,
Addendum G), so the command and its `.kbmap` have been removed (D11, P6).

### Addendum E — Per-directory `.kb/` vs. top-level mirror

A single top-level `.kb/` mirroring the whole tree was rejected: it is a second
structure that must be kept consistent with the real tree on every move/rename. A
per-directory `.kb/` inherits the real tree's structure for free and travels with
its source. Hidden dotfiles are slightly easier to forget, but routine
regeneration (kbi / roll-up) surfaces them, so the risk is low.

### Addendum F — Scope as enabled file types; `file_types` replace semantics

Increment A wiring surfaced two things. First, kbi discovers files with `os.walk`,
which descends into hidden directories, so cards under `.kb/` are found with no
glob change — the dot-directory worry was unfounded for this codebase. Second,
the natural place to express *what gets indexed* is the set of enabled
`file_types`: a card is its own type keyed on the compound `.kb.md` extension, so
"distilled-only" vs "deep" is just which types a config turns on (D12). For that
to work, an explicit `file_types` had to **replace** the defaults rather than
merge into them — the prior merge behavior silently re-added the default
`markdown`/`freeplane` types, making a card-only scope impossible. The trade-off
is that any config specifying `file_types` must now list *every* type it wants;
this is explicit and was already true of existing configs.

### Addendum G — Capturing remote sources (URLs); transcript as source of truth

A common use is "summarize a YouTube sermon/talk and add it to the KB." The card
schema already allows a URL `source`, but a card cannot be *co-located* with a
remote source, and an early idea — hiding the fetched transcript inside `.kb/` —
left the directory visibly empty and gave `-resegment` nothing local to act on.
The resolution: treat the fetched **transcript as the visible local source
document** (the sermon's `Plan.md`), so the directory is a normal "directory of
documents," browsable and re-segmentable, with the card sidecar in `.kb/`.

Capture is a *lossy, sticky projection* of the video onto text: once captured,
every automated step (distill, reconcile, drift via `source_hash`) reads the
transcript, not the video. This is correct for spoken-word content (the transcript
is ~the whole message) and is made honest by two devices: the URL is always
retained in `source` as the canonical original (the real fallback), and
`meta.capture` records the fidelity. So there are two tiers — the local capture is
the *operational* source of truth; the URL/video is the *canonical* one.

Visual richness cannot be detected cheaply (knowing requires looking at the video,
~as costly as processing it), so the system never auto-decides: default is
transcript-only, and a cheap scan of the transcript for visual-reference phrases
("as you can see on this slide…") *warns* when transcript-only is likely lossy.
Higher-fidelity **visual/multimodal capture** (`transcript+visual` = spoken text +
OCR'd on-screen text + short visual descriptions) is **opt-in (`-visual`) and
documented-but-deferred**. Crucially it changes nothing architecturally — it only
produces a richer *local text* capture, so distill/reconcile are unaffected and
the implementation can be slotted in later. Keeping the capture visible and
editable is also a feature: messy auto-transcripts can be cleaned, then re-distilled.

This capture role is the residual purpose previously earmarked for `/kb-import`
(Addendum D), now folded into `/kb-card`, so `/kb-import` can be retired.
