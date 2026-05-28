---
name: dev-workflow
description: |
  The end-to-end cube-new development loop — branch, implement, gate, MR,
  deploy. Enforces the develop-only branch model, the 3-layer quality gate
  (husky -> pr:check -> CI), and hands off to write-codes / pr / qa skills at
  the right steps. Use when starting any feature or fix, when asked "start a
  task", "new branch", "implement X", "how do I work here", "dev loop", or
  before opening any MR. This is the spine; write-codes/pr/qa are the limbs.
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# cube-new dev workflow (spine)

This is the **mandatory** loop for every code change in cube-new. It is strict:
do not skip or reorder steps, never proceed past a failing gate. The other
skills plug in: `vcodes-write-codes` (step 2), `vcodes-pr` (step 6), `vcodes-qa`
(testing). Coding rules live in `docs/refactor/14-coding-standards.md`.

## Hard rules (non-negotiable)

1. **Branch model**: `feat/*` · `fix/*` · `docs/*` · `chore/*` branch from **`develop`**; **their MRs target `develop`.** `main` is **not frozen** — it changes **only** through a deliberate `develop → main` release MR (step 9), made when a production deploy is decided. What's prohibited: direct local commit/push to `main`, and opening a feature MR straight into `main`. (A PreToolUse hook blocks local commit/push on `main`; the server-side release MR merge is unaffected.)
2. `develop` merge → DevOps Jenkins auto-deploys **UAT** (`api-cube-sh.io.linksfield.net`). Production = a deliberate `develop → main` MR (lead-approved) → auto-deploys **PROD** (`api.iotcube.link`).
3. **Deploy is DevOps-owned (Jenkins).** Developers do not create/maintain Dockerfile, k8s templates, nginx conf, or Jenkinsfile until DevOps clarifies ownership. Dev's job = green MR into `develop`.
4. Never `--no-verify`, `--amend` (after review), `--no-gpg-sign`, or force-push shared branches. A failed pre-commit/pre-push → new commit after fix, not amend.
5. Line endings **LF** only. No `console` (`logger.ts`), no `any`, `===` always, named exports only.
6. Every change adds tests. Never weaken a gate to make it pass.
7. **Double gate**: start only on an `intake::accepted` issue (run `intake-review`); pass `pr-eval` before merge. Rubric: `docs/quality-rubric.md`.

## The loop

### Step 0 — Setup (once per machine / when deps missing)

```bash
git rev-parse --abbrev-ref HEAD            # confirm you are NOT on main/develop
[ -d node_modules ] || npm install         # gates can't run without deps
```

If `node_modules` is missing, **stop and install first** — husky and `pr:check` are no-ops without it.

### Step 1 — Branch

```bash
git fetch origin --prune
git checkout -b feat/<scope>-<short> origin/develop
```

**Entry gate**: only branch from an issue labeled `intake::accepted` (run the `intake-review` skill first — `docs/quality-rubric.md` Gate 1). One branch = one logical change. Reference the work item: matrix row(s) from `docs/refactor/0{3,4,5}-*matrix.md` and/or the Jira key (e.g. `P4-5747`).

### Step 2 — Plan, then implement → invoke `vcodes-write-codes`

- Output a short numbered plan first; for non-trivial work, **stop for approval**.
- Implement in **one controllable batch**. Apply the write-codes cube-new rules: folder buckets, no cross-feature imports, `src/api/*` is the only axios owner, shadcn/AntD only, file ≤400 / fn ≤80 / complexity ≤12, zod at API boundaries, branded IDs.
- UI changes: re-read `docs/design.md`; match Figma in Dark + Light; capture screenshots for the MR.

### Step 3 — Build

```bash
npm run typecheck && npm run build
```

Fix until green. Never continue past a broken build.

### Step 4 — Test → `vcodes-qa` for E2E

```bash
npm run test          # unit (vitest)
npm run test:e2e      # e2e (playwright) — see tests/INSTRUCTIONS.md
```

≥ 80% line coverage on `src/{api,lib,stores,hooks}`. Selectors: `getByRole`/`getByPlaceholder`/`getByLabel`/`getByText`. Never `waitForTimeout`. Cover the error path, not just happy path.

### Step 5 — Self gate (must pass before MR)

```bash
npm run pr:check      # lint + typecheck + test + jscpd + build + feature-e2e -> PR-REPORT.md
```

This mirrors CI. Local pass = CI pass. If it fails, fix — do not skip.

> **Husky is only a fast subset, not the gate.** pre-commit = `lint-staged`; pre-push = `typecheck` + `test:staged` (related tests, **no coverage**). Coverage thresholds (R10: 80/70 on `src/{api,lib,stores,hooks}`) are enforced **only** by `npm run pr:check` and CI — never by husky. So always run `pr:check` as your real pre-MR self-check; passing husky does not mean you'll pass CI.

### Step 6 — MR → develop → invoke `vcodes-pr`

- Title: conventional-commit, ≤70 chars (`feat(<scope>): …`).
- Description **must** include `PR-REPORT.md`, the matrix row IDs, and (UI) Dark+Light screenshots.
- **Target branch = `develop`.** Confirm before creating:

```bash
glab mr create --target-branch develop -t "<title>" ...   # -t is --title; or API: target_branch=develop
```

- Run `/review` (or the review skill) before requesting merge. Address CRITICAL before merge.

### Step 7 — CI green

GitLab CI (`quality` = pr:check mirror; `e2e` source-change-gated blocking) must be green. If CI fails but local passed, suspect env drift — don't merge.

### Step 8 — Merge → UAT verify

- Merge into `develop` (approved + CI green). Source branch auto-removed.
- DevOps Jenkins auto-deploys UAT. **Verify on the UAT URL** (login, the changed flow, Dark/Light).

### Step 9 — Release to production (deliberate, lead-only)

- Open `develop → main` MR. This is the only path to `main`.
- Merge → Jenkins auto-deploys PROD. Watch canary / errors post-deploy.

## Definition of Done

- [ ] On a `feat/*` branch off `develop` (never main)
- [ ] `npm run pr:check` green; `PR-REPORT.md` matches HEAD
- [ ] Tests added; coverage threshold met; error paths covered
- [ ] MR targets `develop`, includes report + matrix IDs (+ screenshots if UI)
- [ ] `/review` run; CRITICAL addressed
- [ ] CI green; merged; UAT verified

## Skill map

| Step                       | Skill                |
| -------------------------- | -------------------- |
| entry gate (before step 1) | `intake-review`      |
| 2 implement                | `vcodes-write-codes` |
| 4 test / QA                | `vcodes-qa`          |
| 6 MR                       | `vcodes-pr`          |
| exit gate (before merge)   | `pr-eval`            |
| review                     | `/review`            |
