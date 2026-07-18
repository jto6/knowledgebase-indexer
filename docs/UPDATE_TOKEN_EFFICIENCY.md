# Token-Efficient --update: Analysis and Design

Status: **Phases 1–3 implemented** (Phase 1 2026-07-17: D1, D7, D8 in
`kbi.py`; Phase 2 2026-07-18: D2 `excluded:` section + hashed
`supersedes`/`exported_as` entries; Phase 3 2026-07-18: D3 delta handoff
(`_dir_content_delta` + `--delta` file + skill contract), D5 `kbi hash` /
`kbi manifest-sync` helper verbs (which also canonicalized the previously
agent-improvised `dir_hash` formula), D6 git-recoverable ≤200-line diffs
embedded per changed source, `.mm` diffed at the mm2md level). Phase 4
2026-07-18: D4 complete — `decided: auto|user` + `decided_on` markers on
excluded/absorbed entries, `kbi decisions` audit verb, `status: pending`
persist-plan-first checkpointing (kbi treats pending entries as work to
resume; the delta lists them), and the `Decisions made` report section
embedded in auto-commit message bodies. All phases are implemented; the
behavior is captured normatively as PRD §6 (R-UPD-STALE/DELTA/LOOP/HELP).
Tests in `tests/unit/test_update_staleness.py`; documented in
`REFERENCE.md` §3.1/§3.2/§5.7/§5.8 and `kb-card.md`. Motivating incident:
the 2026-07-17
`./kbi.py configs/Study25-cards.yml --update` run found 14 stale directories
and exhausted the five-hour token window after ~10 of them, even though most
directories had tiny or zero real changes.

This document analyzes where the tokens went and proposes changes to
`kbi.py`, the `segmentation.yml` manifest, and the `/kb-card` skill so that
update cost scales with the **size of the change**, not the size of the
directory — and so that decisions already made are never re-litigated.

## 1. Analysis of the 2026-07-17 run

Each stale directory is refreshed by `subprocess.run(['claude', '-p',
'/kb-card'], cwd=d)` (`kbi.py:677`). Two structural facts drive nearly all
of the waste:

1. **The invocation carries no information.** `kbi.py` has already computed
   which sources changed (it hashed every tracked source in
   `_dir_content_changed`, `kbi.py:499`) — then it throws that result away
   and invokes a bare `/kb-card`. The agent re-derives the delta from
   scratch: re-listing, re-hashing, re-reading, re-running the pairwise
   near-duplicate scan over **all** files (kb-card Step 2.1), every run.
2. **The manifest records only positive decisions.** `segmentation.yml`
   records cards (and `supersedes`/`exported_as` on them), but not the
   *negative* decisions: files evaluated and deliberately not carded,
   judgment calls answered at the review gate. Those get re-evaluated — and
   re-asked — on every run.

### 1.1 Waste modes observed, mapped to the transcript

| ID | Waste mode                                 | Evidence (run #)                                    |
|----|--------------------------------------------|-----------------------------------------------------|
| W1 | False stale: superseded file looks "new"   | [3] SDV: full run to conclude "everything current"  |
| W2 | Headless review-gate deadlock              | [1] PersDev, [2] LiveAtChoice: plan built, then     |
|    |                                            | "Reply go" — impossible under `claude -p`; nothing  |
|    |                                            | persisted; full analysis repeats next run           |
| W3 | No decision memory (exclusions, judgments) | [2] Delme.mm/templates re-judged; [6],[9] LICENSE,  |
|    |                                            | logs, prompt scratch re-classified as "skip"        |
| W4 | Delta re-derived by the agent              | all runs; [3] even hashed the mm2md output first    |
|    |                                            | (wrong signal) and had to redo the comparison       |
| W5 | Unchanged content re-read "to verify"      | [3] all 7 sources; [8] unaffected cards "verified   |
|    |                                            | still accurate" despite matching hashes             |
| W6 | Mechanical bookkeeping done by the model   | [9] reverse-engineered the `dir_hash` serialization |
|    |                                            | by reproducing the prior value; hand-edited YAML    |
| W7 | Cosmetic drift gets a full semantic run    | [9] only `.svg`→`.drawio.svg` link renames; 4 cards |
|    |                                            | touched, bodies unchanged                           |
| W8 | Loop continues after hard budget failure   | [11]–[14] four consecutive spend-limit failures     |

### 1.2 W1 is a plain bug (confirmed)

`_dir_content_changed` builds `seen_sources` from each card's `source` only.
Files recorded under a card's `supersedes:` or `exported_as:` lists are
**not** added. The new-file check (`kbi.py:585`) then treats any
still-present superseded file with a tracked extension as an untracked new
source and returns stale.

Confirmed in `~/TIGoogleDrive/MyMaps/Notes/SDV`: `SDV2.mm` exists on disk,
appears only under `supersedes:` in the manifest, and re-triggers staleness
on every run. (`Piyali1-1.mm.conflict1` is saved only by the `*.conflict*`
default exclude.) Run [3] — a complete Claude invocation — was 100% waste,
and will recur on every future run until fixed. Every directory that keeps a
superseded or format-export file on disk has the same trap.

### 1.3 W2 is the single largest waste

Runs [1] and [2] performed the full segmentation analysis (PersDev: 36
files, ~34 proposed cards; LiveAtChoice: ~20 files), then stopped at the
Step 2.3 review gate asking questions that `claude -p` can never answer.
Nothing was written to `segmentation.yml`, so the directories remain stale
and the **entire analysis will be re-done from scratch on the next run** —
an unbounded repeated cost. The "why is it re-deciding the Quarterly Goal
Tracker supersession?" symptom is exactly this: the decision *was* made last
run, but the deadlock prevented it from ever being persisted.

## 2. Design

Guiding principles:

- **Decisions are made once and persisted; unchanged inputs mean the
  decision stands.** (User requirement — the manifest is the memory.)
- **Deterministic work never spends tokens.** Hashing, delta computation,
  manifest field updates, and git commits belong to `kbi.py`, not the model.
- **The agent's context scales with the delta**, never with directory size.
- **Every run persists its progress** so an interrupted run resumes instead
  of restarting.

### D1. Fix the false-stale bug (kbi.py only, zero tokens)

In `_dir_content_changed`, add every path resolved from each card's
`supersedes:`, `exported_as:`, and `refines:` lists to `seen_sources`
before the new-file scan. Content changes to a superseded file still don't
matter (it has no `source_hash` to compare — correct: it is absorbed), but
its mere presence no longer marks the directory stale.

### D2. Decision memory in `segmentation.yml`

Add a top-level `excluded:` section — the negative counterpart of `cards:`:

```yaml
excluded:                          # evaluated, deliberately not carded
  - path: ../Delme.mm
    reason: disposable-by-name     # short, human-auditable
    source_hash: sha256:...        # decision stands while this matches
  - path: ../RtoI Template.mm
    reason: template-no-knowledge
    source_hash: sha256:...
```

Semantics:

- `/kb-card` records an entry whenever it (or the author at the review
  gate) decides a file should not become a card. It never re-evaluates an
  excluded file whose hash still matches; if the hash drifts, the file is
  re-surfaced as **new** (the decision's input changed, so the decision is
  re-opened — the only time re-asking is legitimate).
- `kbi.py`'s new-file staleness check treats an untracked file with a
  matching `excluded` entry as tracked-and-unchanged.
- Empty/near-empty files ("exclude silently") get entries too — silence
  should still be durable.

**Absorbed sources also get hashes.** Phase 1's D1 fix makes files listed
under `supersedes`/`exported_as` invisible to the staleness scan — correct
for their mere presence, but it also means *editing* a superseded file goes
unnoticed. Phase 2 upgrades the manifest entries to carry a hash per
absorbed path:

```yaml
supersedes:
  - path: ../Quarterly Goal Tracker.mm
    source_hash: sha256:...          # decision stands while this matches
```

(The bare-string form remains accepted for backward compatibility and means
"no hash tracked".) When an absorbed file's hash drifts, the supersession
decision is re-opened: the file is re-surfaced as **new** at the next update
and re-classified — maybe it is still superseded, maybe it has diverged into
a document of its own. Deleting an absorbed or excluded file simply prunes
its entry at the next reconcile (nothing to re-decide; the canonical card's
`refines:` pointer is dropped).

Together with `supersedes`/`exported_as` (already sticky once written), this
makes every review-gate answer durable, and re-opens a decision exactly when
its input changes — never otherwise. Nothing about an unchanged file is
ever asked twice.

### D3. Delta handoff: kbi computes, the agent consumes

`_scan_managed_directories` already computes everything needed. Capture it
instead of discarding it, and write a per-directory delta file before each
invocation (scratch location, e.g. `/tmp/kbi-update/<slug>.delta.yml`):

```yaml
directory: /home/jon/MyGoogleDrive/MyMaps/PersDev
scope: non-recursive
unchanged: 16                      # count only — agent must not touch these
changed:
  - path: Journal.mm
    old_hash: sha256:aaaa...
    new_hash: sha256:bbbb...
    cards: [journal, journal-2015] # slugs bound to this source
new:
  - path: New Year Questions 2016.mm
deleted:
  - path: OldNotes.mm
    cards: [old-notes]
```

Invoke `claude -p '/kb-card --delta /tmp/kbi-update/<slug>.delta.yml'`.

Skill contract changes (kb-card.md):

- **Trust the delta.** Unchanged sources: zero reads, zero re-hashing, no
  "verify still accurate" passes (kills W4/W5). The hashes in the delta are
  authoritative — never recompute them (kills the mm2md wrong-hash detour).
- **Near-duplicate scan is delta-scoped**: compare *new* files against
  existing sources/cards only — never all-pairs over the directory.
- Cards whose source is unchanged are not re-tagged, re-linked, or touched.

### D4. Headless auto mode with durable judgment calls

`--update` invokes `/kb-card --delta ... -auto`. In `-auto` mode:

- The Step 2.3 review gate does not block. For each judgment call the skill
  applies its recommended option (the one it would have bolded), executes,
  and **records the decision durably** (`supersedes`/`exported_as`/
  `excluded` entries as appropriate).
- The run report lists every auto-applied judgment under a `Decisions made`
  heading so the author can audit and override later (an override edits the
  manifest; `-resegment` remains the big hammer).
- **Auto decisions are marked for review.** Every entry written in `-auto`
  mode (a `supersedes`/`exported_as`/`excluded` record, an auto-confirmed
  orphan retirement) carries `decided: auto` and `decided_on: <date>` in the
  manifest. Review paths, in order of convenience:
	- the `Decisions made` section of the run report (also present in the D8
	  auto-commit's message body, so `git log` in the KB repo is a durable
	  decision journal);
	- `./kbi.py decisions [<dir>]` — a Phase 4 helper verb listing all
	  `decided: auto` entries across managed directories, newest first, so
	  nothing scrolls away with the terminal;
	- accepting is free (do nothing); overriding is an edit to the manifest
	  (or an interactive `/kb-card` run), which flips the entry to
	  `decided: user` — user decisions are never auto-revisited while their
	  recorded hash matches.
- **Persist before authoring**: write the reconciled `segmentation.yml`
  (new entries carry `status: pending` or simply no card file yet) *before*
  writing card bodies, and update each entry as its card is authored. An
  interrupted run (spend limit, crash) resumes with the plan and all
  decisions intact — only unauthored bodies remain. This alone converts the
  W2 deadlock from "repeat everything forever" to "pay the analysis once."

Interactive runs of `/kb-card` (typed by the author) keep the review gate
exactly as today.

### D5. Mechanical helper subcommand (no model bookkeeping)

New maintenance verbs on `kbi.py`, for the skill to shell out to:

```bash
./kbi.py hash <file>...        # canonical sha256:<hex> per file (raw bytes)
./kbi.py manifest-sync <dir>   # recompute+rewrite source_hash for tracked
                               # sources, dir_hash, dir_fingerprint, updated
```

The skill is instructed to use these instead of hand-rolling hashes or
reverse-engineering serializations (kills W6, and removes a whole class of
"which bytes do I hash?" errors — the answer is always: don't; call the
tool). `manifest-sync` is also the last step of every `/kb-card` run, so
fingerprints are always written by the same code that checks them.

### D6. Small-diff fast path (optional, biggest per-token lever for W7)

For each `changed` entry whose unified diff is small (default cap: 200
lines; `.mm` sources diffed via their `mm2md` conversion), embed the diff in
the delta file. Skill contract: when a diff is present and no card boundary
is plausibly affected, refresh from **existing card + diff** without reading
the full source. Cosmetic drift (run [9]'s link renames) then costs one
short read instead of a full re-distillation pass; if the diff cap is
exceeded or boundaries look affected, fall back to reading the source.

### D7. Fail fast on budget exhaustion

In `run_update`, on a nonzero return code whose output matches known limit
messages ("hit your monthly spend limit", "usage limit"), or on two
consecutive failures, **abort the remaining loop** with a message listing
the directories still stale (they will be picked up next run). Runs
[11]–[14] burned four invocation attempts against a hard wall.

### D8. Auto-commit card updates in git repositories (enhancement)

After a successful per-directory refresh (`rc == 0`), `run_update`:

1. Detects a work tree: `git -C <dir> rev-parse --is-inside-work-tree`.
2. Stages **only** that directory's card state:
   `git -C <dir> add -A -- .kb` (covers modified/added/retired cards and
   the manifest; `-A` with the explicit `.kb` pathspec picks up deletions
   while making it impossible to sweep in unrelated changes).
3. Commits only if something is staged
   (`git -C <dir> diff --cached --quiet -- .kb` fails), with:

   ```
   kb: refresh knowledge cards for <repo-relative-dir> (kbi --update)

   Signed-off-by: <git config user.name> <git config user.email>
   ```

   Identity resolved from the repository's own git config. No AI
   attribution trailers.
4. Never pushes; never commits paths outside `<dir>/.kb/`. Pre-existing
   staged changes elsewhere in the repo are untouched (the commit uses the
   explicit pathspec on `git commit` as well: `git commit -- .kb` semantics
   via committing only what step 2 staged — implemented by verifying the
   staged set is confined to `.kb/` before committing, else skip with a
   warning).

Escape hatch: `--update --no-commit` CLI flag; per-area opt-out
`update_commit: false` in `kb.yml`. Default: commit when in a repo.

Implemented in `kbi.py` (deterministic, zero tokens) — not in the skill.

## 3. Expected cost profile after the changes

| Scenario                               | Today                         | After                         |
|----------------------------------------|-------------------------------|-------------------------------|
| Unchanged dir, superseded file on disk | full run, "all current" (W1)  | no invocation                 |
| Unchanged dir, mtimes churned by sync  | no invocation (already OK)    | no invocation                 |
| Small edit to one carded source        | full-dir re-derivation        | delta + diff + that card only |
| New file added                         | full-dir re-derivation + gate | delta-scoped analysis, auto-  |
|                                        | deadlock in headless mode     | decided, decision persisted   |
| Previously excluded file, unchanged    | re-judged every run           | skipped (manifest `excluded`) |
| Run interrupted mid-directory          | all analysis lost, repeats    | resumes from persisted plan   |
| Budget exhausted mid-update            | keeps burning failed calls    | aborts, lists remainder       |

## 4. Implementation plan

Phased so each step lands value independently; phases 1–2 need no skill
changes beyond documentation.

1. **Phase 1 — kbi.py only (highest value : effort ratio).**
   D1 (seen_sources bug fix), D7 (fail fast), D8 (git auto-commit).
2. **Phase 2 — manifest schema.** D2 `excluded:` section: honor it in
   `_dir_content_changed`; document in `REFERENCE.md`; teach `/kb-card` to
   write it.
3. **Phase 3 — delta handoff.** D3 delta file + `--delta` skill contract,
   D5 helper subcommands, D6 small-diff fast path.
4. **Phase 4 — headless auto mode.** D4 `-auto` + persist-plan-first
   checkpointing in kb-card.md.

PRD alignment: these should be captured as requirements (suggested IDs:
R-UPD-DELTA-001…, R-UPD-DECISION-001…, R-UPD-COMMIT-001…) in
`docs/kbi_PRD.md` when the design is accepted, per the project's
PRD-first rule.
