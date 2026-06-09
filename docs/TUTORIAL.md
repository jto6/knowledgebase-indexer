# Knowledge Base System — Tutorial

A quick, example-driven getting-started guide. It is not exhaustive — see
`REFERENCE.md` for the full schema and semantics.

## The two sides

- **Author cards** with `/kb-card` *inside a content repo*. Cards live in `.kb/`
  folders and are committed with that repo.
- **Build the catalog** with `kbi` (run separately). It reads cards read-only and
  writes a per-domain navigational **index** that consumers read.

This guide follows those two sides: first creating and maintaining cards, then
building and using the catalog.

Each area has a small config (`kb.yml`) telling `/kb-card` the domain and how to
distill. You don't have to create it yourself — on the first run in a new area,
`/kb-card` creates `.kb/` and asks a couple of questions to write a default one
(or pass `-domain` to skip the prompt). You can also author it directly;
everything beyond `domain` is an optional override:

```yaml
# <area-root>/.kb/kb.yml
domain: spiritual
profile: reflective          # reflective = include key quotes; standard = none
seed_tags: [faith, grace, discipleship]
```

## Part 1 — Creating and maintaining cards

Author-side: run `/kb-card` inside the content repo; cards and `segmentation.yml` are
committed there.

### Authoring is one command — the tool adapts to the content

You run the same command every time — `/kb-card` for the current item, or
`/kb-card -r <area>` to walk a tree. You do **not** pick a granularity mode; the
tool reads the content and decides how many cards it warrants. Identical commands
produce different results purely from *what is being indexed*:

| Content being indexed                                             | What the tool produces          |
|-------------------------------------------------------------------|---------------------------------|
| a small, single-topic repo                                        | one card for the whole repo     |
| subdirectories each a cohesive item (BSFL: one lesson per folder) | one card per directory          |
| a directory of distinct documents                                 | one card per file               |
| a dense, multi-topic document                                     | several cards, split by section |

```bash
cd ~/dev/BSFL
/kb-card -r "Fall 2025"      # one card per lesson — each folder is one lesson

cd ~/dev/research/SDV-research/reports
/kb-card -r .                # one card per report, and the dense ones split further
```

Both invocations are the same in form; the difference in output comes entirely
from the material. To preview what the tool intends *before* it writes anything,
run with `-plan` first (see Overrides).

### Capture a talk from a URL (e.g. a sermon)

A remote source (a YouTube sermon) has no local home, so `/kb-card` captures it
first: it downloads the **transcript**, writes it as a visible local file, and
distills a card whose `source` links back to the video.

```bash
cd ~/dev/sermons          # an area with its own .kb/kb.yml (e.g. domain: spiritual)
/kb-card https://www.youtube.com/watch?v=XXXXXXXX
```

Result: a visible transcript `sermons/<slug>.md` (the browsable, re-segmentable
source) and a card `sermons/.kb/<slug>.kb.md` whose `source` lists the YouTube URL
(to watch later) plus the local transcript. The video file itself is never kept.

Transcript-only is the default and is right for spoken-word talks; a richer
`-visual` capture for slide-heavy videos is planned but not yet available.

### Overriding the adaptive choice

When you want a result the tool would not pick on its own, declare it in the
area's `kb.yml` (applies to the subtree) or pass a flag:

- **Force the unit** — `card_unit: file` pins one card per file (or `directory` /
  `repo` to go coarser) instead of letting the tool decide.
- **Forbid splitting** — `card_split: never` keeps a dense, multi-topic file as a
  single card (the adaptive default would split it). `auto` just states the
  default explicitly.
- **Set the depth** — `card_density: coarse|normal|fine|exhaustive`, or per run
  `-density fine`; cap with `-cards N` (a **maximum**, never a quota — it will not
  invent topics to reach N).
- **Review before authoring** — `-plan` proposes the segmentation into `segmentation.yml`
  and stops. Edit it (merge / split / relabel, or add a `density_overrides` entry
  to go deeper on one section), then run without `-plan` to author.

```yaml
# reports/.kb/kb.yml — force outcomes the adaptive default wouldn't choose
card_split: never        # one card per report, even the dense multi-topic ones
# card_unit: file        # or: pin one card per file
# card_density: fine     # or: when splitting, split deeper
```

```bash
/kb-card -plan Hypervisor_Technologies.md          # propose the split; review segmentation.yml
/kb-card -density fine Hypervisor_Technologies.md  # deeper: ~ one card per section
/kb-card -cards 8 Hypervisor_Technologies.md       # at most 8 cards (never pads to 8)
```

### Maintaining cards as content changes

Edit a source, then re-run `/kb-card` over the area; it **reconciles** against
`segmentation.yml` and only acts on what changed:

```bash
/kb-card -r reports/          # refresh drifted cards, re-segment broken
                              # boundaries, flag orphans, propose new sections
```

You never redo settled decisions — locked boundaries persist; only genuinely
changed content is re-reviewed. (See `REFERENCE.md` §4.4 for the reconcile
outcomes.) Regenerate the catalog afterward (Part 2).

## Part 2 — Building and using the catalog

Catalog-side: run `kbi` separately; it reads the `.kb.md` cards read-only and
produces the catalog that consumers read.

### Build the catalog and read it

Write a catalog config that scopes to cards only (`card` file type) and uses the
markdown renderer, then run `kbi`.

```yaml
# configs/catalog.yml (in the kbi repo)
directories:
  include: ["/home/jon/dev/BSFL", "/home/jon/dev/research/SDV-research"]
  exclude: ["**/.git/**", "**/__pycache__/**"]
keywords: { files: [] }
output: { file: "/home/jon/dev/kb/index", format: "markdown" }
types:
  include: [card]
```

```bash
cd ~/dev/kbi
python3 kbi.py configs/catalog.yml
#   → ~/dev/kb/index/<domain>.md  (one index per domain) + INDEX.md
```

Open a domain index (e.g. `~/dev/kb/index/spiritual.md`) — a **navigational index**
of links, not content. Scan its File System / Tags sections to find candidate
cards, then open the linked cards to read their concepts.

#### Or render a mind map instead

The same index model also renders to a Freeplane `.mm` mind map (the human
navigation view). Switch `format` to `freeplane` and point `output.file` at a
`.mm` file — same card-only scope:

```yaml
output: { file: "/home/jon/dev/kb/catalog.mm", format: "freeplane" }
types:
  include: [card]
```

```bash
python3 kbi.py configs/catalog-mm.yml      # → /home/jon/dev/kb/catalog.mm
```

Open `catalog.mm` in Freeplane to browse the File System and Tag branches over
your cards. (A Word index branch is available but **opt-in** — add
`output.views: { word: on }` — since it is heavy; for ad-hoc full-text lookups
prefer `kbi search`, below.)

#### Search just the indexed files

Instead of materialising a word index, search the exact set of files a config
covers with ripgrep (falling back to grep):

```bash
python3 kbi.py search configs/catalog.yml "covenant" -i
python3 kbi.py search configs/catalog.yml "TODO" -l     # list matching files
```

Arguments after the pattern pass straight through to the backend.

To deep-index **one repo's raw content** (the original kbi use) *without* the
card summaries, scope to that repo and exclude the `card` type:

```yaml
directories: { include: ["/home/jon/dev/research/SDV-research"] }
keywords: { files: [] }
output: { file: "/home/jon/dev/research/SDV-research/index.mm", format: "freeplane", partition_by_domain: "off" }
types: { exclude: [card] }   # index everything except the .kb.md card summaries
```

This indexes every document (and parses cards card-aware), producing a full
local navigation map of the repo.

### Wire a consumer (e.g. a council member)

The retrieval protocol is shared once; each member just declares its slice.

```markdown
<!-- advisor/CLAUDE.md (shared, once) -->
## Knowledge Base Access
Slice location: /home/jon/dev/kb/index/<domain>.md
Protocol: scan the index by tag/title → open the 1–3 linked cards → read their
content (follow a card's `source:` only for the original).
```

```markdown
<!-- advisor/pastor/CLAUDE.md (per-member subscription) -->
## Knowledge Base Access
Subscribed slice: /home/jon/dev/kb/index/spiritual.md — apply the council's
shared retrieval protocol.
```

A member-only session picks up the shared protocol automatically (CLAUDE.md loads
up the directory tree).

## Cheat sheet

| Goal                         | Command                                      |
|------------------------------|----------------------------------------------|
| Author cards (tool adapts)   | `/kb-card` · `/kb-card -r <root>`            |
| Preview before authoring     | `/kb-card -plan <file>`                      |
| Force one card per file      | `card_unit: file` in `kb.yml`                |
| Never split a dense file     | `card_split: never` in `kb.yml`              |
| Split deeper / cap the count | `/kb-card -density fine <file>` / `-cards N` |
| Re-segment a changed source  | `/kb-card -resegment <file>`                 |
| Build the catalog            | `python3 kbi.py <catalog.yml>`               |
