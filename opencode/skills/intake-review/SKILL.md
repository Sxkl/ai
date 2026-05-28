---
name: intake-review
description: |
  Entry gate — evaluate a new GitLab issue (feature/bug) against the project
  docs BEFORE any work starts. Runs binary gates (red-line / wrong-layer /
  duplicate), scores 5 dimensions per docs/quality-rubric.md, posts a
  structured comment, and applies intake::* labels. Use when asked to "triage
  issue", "intake review", "should we build this", "evaluate issue #N", or
  before branching for any new feature/bugfix.
allowed-tools: [Bash, Read, Grep, Glob]
---

# Intake review (entry gate)

The front door. Apply **Gate 1** of `docs/quality-rubric.md`. Keep it fast (minutes), terse, evidence-based. Binary gates override the score. Lead may override.

## Steps

1. **Read the issue** (`gitlab_get_issue` or API) and the rubric. Read the relevant SoT docs: `project-plan.md`, `refactor/00-master-plan.md` (red lines, out-of-scope), `03/04/05` matrices, `08b` (current phase), `14-coding-standards.md`.
2. **Binary gates**: red-line violation? wrong layer (backend/DevOps)? duplicate? — check matrices + open issues; `kg_concept_search`/`kg_rag_search` for existing concepts (cross-check against docs; KG can be stale).
3. **Score** the 5 dimensions (0-2 each): scope fit · clarity · value/priority · feasibility/sizing · test+impact awareness.
4. **Comment** on the issue: gate results + per-dimension scores + verdict + required fixes (if needs-info).
5. **Label**: `intake::accepted|needs-info|rejected|deferred` + the score (in the comment) (+ `type::*`, `scope::*`, `redline:flag`).

## Rules

- A failed binary gate ⇒ `rejected` (unfixable) or `needs-info` (fixable), regardless of score.
- Only `intake::accepted` issues may be branched (see `dev-workflow`).
- Don't bureaucratize — this is a quick sanity gate, not a committee.
