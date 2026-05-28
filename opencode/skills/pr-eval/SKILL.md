---
name: pr-eval
description: |
  Exit gate — evaluate an MR diff against the project docs AND the accepted
  issue (the scope contract) before merge. Runs binary gates (red-line /
  scope-drift / missing-requirement), scores 5 dimensions per
  docs/quality-rubric.md, posts a verdict comment, and applies pr-eval::*
  labels. Complements pr:check (mechanical) and vcodes-pr (taste) with a
  rubric-scored verdict. Use when asked to "evaluate this MR", "pr eval",
  "is this mergeable", or before merging to develop.
allowed-tools: [Bash, Read, Grep, Glob]
---

# PR-eval (exit gate)

The back door. Apply **Gate 2** of `docs/quality-rubric.md`. This is the **judgment** layer — the **mechanical** layer (`pr:check` / CI `quality`) must already be green.

## Steps

1. **Get the diff** (`git diff origin/develop...HEAD`) and the **linked accepted issue** (the scope contract).
2. **Binary gates**: red-line violation (cross-feature import, tenant isolation, additive-only — judgment beyond lint)? scope drift (built beyond the issue)? missing core requirement?
3. **Score** the 5 dimensions (0-2 each): scope conformance · red-line/principle compliance · architecture/doc conformance (02/06/14) · test quality (error paths) · maintainability. Optional: `kg_context_for_pr`/`kg_impact_analysis` for blast radius (cross-check against docs).
4. **Comment** on the MR: gate results + per-dimension scores + verdict + required changes.
5. **Label**: `pr-eval::pass|concerns|block` + the score (in the comment).

## Rules

- A failed binary gate ⇒ `pr-eval::block`, regardless of score.
- **Non-code diffs (docs / CI / skills / config)**: also run the **Non-code artifact gate** (`vcodes-pr` taste-layer items 10-14: CLI flag correctness, CI exit-code/failure semantics, label/ref/branch consistency, config & script validity, independent pass). Most harness changes are not `.ts` — the code-lens rubric misses them.
- Merge gate: this GitLab is **CE (no required-approval)** — the `pr-eval` verdict + label + reviewer discipline gate the merge; the hard stop is the mechanical CI gate.
- Don't re-run mechanical checks here; assume `pr:check`/CI green.
