---
name: vcodes-pr
description: |
  Two-phase PR/MR workflow: review code quality then prepare submission.
  Supports both GitHub (PR) and GitLab (MR). Phase 1 reviews diff for bugs,
  security, AI anti-patterns, test coverage, and project compliance.
  Phase 2 runs quality gates, generates test report, and produces description.
  Outputs PR-REPORT.md with verdict. Use when asked to "review PR", "submit PR",
  "prepare PR", "code review", "check my diff", "is this ready to merge",
  "ship this", "create PR", "create MR", "submit MR", or before running
  /ship or /land-and-deploy.
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob]
---

# PR/MR Workflow

Two phases: Review → Submit. Report findings — don't fix them.

> ## cube-new project specifics — read first
>
> 0. **MR target = `develop`. Never target `main` with a feature MR; never push/commit to `main` directly.** Branch `feat/*` from `develop`. `develop` merge → UAT; production release is a separate, lead-approved `develop → main` MR. Deploy is merge-triggered, executed by DevOps's Jenkins (not GitLab CI). Developer's job = MR → `develop` + green CI.
> 1. **Always run `npm run pr:check` first.** It executes the full local gate (lint, typecheck, test, jscpd, build, feature-tagged e2e) and writes `PR-REPORT.md`. The MR description must include this report (paste or attach).
> 2. **Blocking checks** are the script-layer ones. **Agent layer adds taste checks** that scripts can't do — see "Agent review (cube-new)" below.
> 3. **MR title format** ≤ 70 chars, conventional-commit prefix:
>    `feat(<scope>): <short>` · `fix(<scope>): <short>` · `docs/refactor/chore: ...`
> 4. **MR description must reference matrix rows**: e.g. `Implements F-SS-01, P-PUB-03, A-OR-NEW-01.` (See `docs/refactor/03-features-matrix.md`, `04-pages-matrix.md`, `05-apis-matrix.md`.)
> 5. **UI-touching MRs** (anything under `src/components/` or `src/features/*/ui/`) must include Dark + Light screenshots. The auto-applied label `needs-design-review` requires Design Lead approval before merge.
> 6. **Auth-touching MRs** must call out the impact in description and link to `02-target-architecture.md §4.A` if any contract changed.
> 7. **Distributor / permission-touching MRs** must include a manual tenant-isolation note (what scope did you check, what audit log appears).
> 8. **Never `--amend` after the user reviewed**. Make a new commit. Never `--no-verify` unless user explicitly says skip; if used, mention it in the MR description.
> 9. **CI is currently a mirror of `pr:check`** (Batch 6). Local pass = CI pass. If CI fails but local passed, suspect env drift.
>
> ## Agent review (cube-new) — taste layer
>
> After `npm run pr:check` is green, before drafting the MR description, do these checks the scripts can't:
>
> 1. **Cross-feature smell**: grep diff for `from '@/features/<other>'`; flag.
> 2. **Magic numbers / strings**: literals that should be enums or env constants.
> 3. **Naming**: any `*Helper.ts`, `*Utils.ts` (banned), `*Manager.tsx` (vague), default-exported components (banned).
> 4. **Dead code / unused imports** beyond what TS catches.
> 5. **Error handling**: every async path → typed error or Result<T>; no `throw 'string'`.
> 6. **Test quality**: meaningful assertions; covers error path, not just happy path.
> 7. **Permission / tenant scope**: if API hooks touched, did they include `X-Tenant-Code`? Cross-check against `docs/refactor/06-permission-model.md`.
> 8. **Design-system compliance**: any `<button>`/`<input>`/`<select>`/`<textarea>`/`<a>` outside `components/ui/`? (Lint catches; double-check anyway.)
> 9. **Matrix row coverage**: every claimed ID is in the diff; every domain folder in the diff maps to a matrix row.
>
> ### Non-code artifact gate (docs / CI / skills / config — these break too)
>
> Most harness/infra changes are NOT `.ts`. Run these whenever the diff touches `*.md`, `.gitlab-ci.yml`, `.claude/**`, `*.json`, `*.sh`, `.gitlab/**`:
>
> 10. **CLI/command examples**: verify every flag in shell commands inside docs/skills (`glab`, `gh`, `git`, `npm`, `npx`, `kubectl`). Don't trust short flags — e.g. `glab mr create -t` is `--title`, NOT target branch (`--target-branch`). When unsure, check `--help`.
> 11. **CI/CD semantics**: if `.gitlab-ci.yml` changed, reason about each job's **exit code / failure mode**, not just syntax. Test runners with a filter need a no-match guard (Playwright → `--pass-with-no-tests`; vitest → `--passWithNoTests`). Check `allow_failure`, `rules`, and `rewrite-target` correctness.
> 12. **Cross-artifact consistency**: labels referenced in docs/skills must **exist** in GitLab and match the scoped form (`intake::accepted`, not `intake:accepted`); referenced files / matrix IDs must exist (broken-ref check); branch/default-branch/protection assumptions must match the real project settings.
> 13. **Config/script validity**: JSON parses (`python3 -m json.tool`), shell scripts are `bash -n` clean (ideally shellcheck), YAML lints, hook paths resolve.
> 14. **Self-authored ⇒ independent subagent review (clean context), BEFORE push**: if you wrote the diff, you have blind spots. **Spawn a fresh subagent with clean context** (Agent tool) to review the diff independently — no authoring bias, no anchoring on your own intent. Give it only the diff + the rubric, not your reasoning. **Timing: run BEFORE `git push`**, against the local staged/unpushed diff. Running after push duplicates the GitLab AI auto-reviewer that fires on every push — wasteful and clutters the MR. If the subagent finds blockers, fix locally and re-run; **push only when the subagent is clean**. Complement (not replace) with `/codex review` or the GitLab AI reviewer (they fire on push). Never rubber-stamp your own work.
>
> Report each finding as **AUTO-FIX** (apply now), **ASK** (batch to user), or **BLOCKING** (must address before merge).
>
> ## Phase 3 (cube-new): MR submission specifics
>
> 1. Verify `PR-REPORT.md` was generated this commit (matches HEAD sha).
> 2. Append the report to the MR description.
> 3. Auto-add the matrix rows table.
> 4. Auto-add the reviewer checklist (already in PR-REPORT.md).
> 5. Auto-suggest reviewers based on touched paths:
>    - `src/features/sim/`, `src/api/modules/sim.ts` → @sim-owner
>    - `src/components/`, `src/styles/` → @design-lead
>    - `src/api/client.ts`, `src/stores/auth.ts` → @auth-owner
>    - `src/features/distributor/`, `src/api/modules/distributor.ts` → @distributor-owner
> 6. Apply labels:
>    - `needs-design-review` if `components/` or `features/*/ui/` touched
>    - `needs-security-review` if `api/client.ts`, `stores/auth.ts`, `stores/tenant.ts`, or any `permission` keyword touched
>    - `needs-perf-review` if any file > 300 lines was added, or bundle-size grew > 5%
> 7. Output the final MR URL.

---

## Platform Detection

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if echo "$REMOTE_URL" | grep -q "github.com"; then
  PLATFORM="github"
elif echo "$REMOTE_URL" | grep -q "gitlab\|git\..*\.net\|git\..*\.com"; then
  PLATFORM="gitlab"
  GITLAB_TOKEN=$(echo "$REMOTE_URL" | grep -o 'glpat-[^@]*' 2>/dev/null)
  GITLAB_HOST=$(echo "$REMOTE_URL" | sed -n 's|.*://[^@]*@\([^/]*\)/.*|\1|p')
  GITLAB_PROJECT=$(echo "$REMOTE_URL" | sed -n 's|.*/\([^/]*/[^/]*\)\.git|\1|p' | sed 's|/|%2F|g')
  GITLAB_API="https://$GITLAB_HOST/api/v4"
else
  PLATFORM="unknown"
fi
echo "Platform: $PLATFORM"
```

Terminology: GitHub uses "PR" (Pull Request), GitLab uses "MR" (Merge Request).
Use the correct term based on detected platform.

## Gather Context (run first)

```bash
BRANCH=$(git branch --show-current)

# Detect base branch
BASE_BRANCH="main"
git rev-parse origin/main &>/dev/null || BASE_BRANCH="master"
git rev-parse origin/develop &>/dev/null && BASE_BRANCH="develop"

BASE=$(git merge-base $BASE_BRANCH HEAD 2>/dev/null || git merge-base origin/$BASE_BRANCH HEAD)
echo "Branch: $BRANCH"
echo "Base branch: $BASE_BRANCH"
echo "Base: $(git log --oneline -1 $BASE)"
git diff origin/$BASE_BRANCH...HEAD --stat
git diff origin/$BASE_BRANCH...HEAD --name-only
git status --short
git log origin/$BASE_BRANCH...HEAD --oneline
cat CLAUDE.md 2>/dev/null
cat docs/design.md 2>/dev/null
```

## Pre-Submit: Conflict Detection

Before review, check for merge conflicts with base branch:

```bash
git fetch origin $BASE_BRANCH
CONFLICTS=$(git merge-tree $(git merge-base HEAD origin/$BASE_BRANCH) HEAD origin/$BASE_BRANCH 2>&1 | grep "changed in both" || true)
```

- **No conflicts** → continue to Phase 1
- **Conflicts detected** → warn user, suggest rebase:

```
⚠️ Current branch has conflicts with {BASE_BRANCH}:
  - {conflicting files}

Recommend: rebase onto origin/{BASE_BRANCH} before submitting.
Proceed with rebase?
```

If user confirms → rebase, then continue.

## Pre-Submit: Existing PR/MR Detection

Check if current branch already has an open PR/MR:

**GitHub:**

```bash
gh pr list --head "$BRANCH" --state open --json number,url 2>/dev/null
```

**GitLab:**

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_API/projects/$GITLAB_PROJECT/merge_requests?source_branch=$BRANCH&state=opened"
```

Decision:

- **Open PR/MR found** → push new commits, it auto-updates. Notify user with URL.
- **No open PR/MR** → create new after review passes.

---

## Phase 1: REVIEW

Review the FULL diff (all commits, not just latest).

### A. Quality Gates

**Gate 1: Clean Working Tree**

- Uncommitted changes that should be in the PR? List and ask user.

**Gate 2: Debug Residue**

```bash
git diff origin/$BASE_BRANCH...HEAD | grep -n "console\.log\|debugger\|TODO.*HACK\|_old\|_backup\|_v2"
```

- `console.log`, `debugger`, `_old`/`_backup`/`_v2` files, commented-out blocks (>3 lines)

**Gate 3: Type Safety**

```bash
git diff origin/$BASE_BRANCH...HEAD -- '*.ts' '*.tsx' | grep -n ": any\|as any"
```

- `any` type, `@ts-ignore` without explanation, missing return types on exports

**Gate 4: Security**

- Hardcoded secrets (API keys, tokens, passwords)
- New API routes without auth middleware
- `dangerouslySetInnerHTML` without sanitization
- Raw SQL string concatenation
- XSS: unescaped user input in rendered output
- CSRF: state-changing GET requests
- Data leakage: returning sensitive fields in API responses

**Gate 5: API Client Compliance**

- No raw `fetch()` — must use project's shared API client
- No repeated headers/auth logic outside the client
- Error handling on all API calls

**Gate 6: Project Compliance**

- Check CLAUDE.md conventions against the diff
- Design system adherence if UI files changed

**Gate 7: Close-Keyword Discipline (BLOCKER)**

GitHub auto-closes any issue whose number appears next to a close keyword (`fix`, `fixes`, `fixed`, `close`, `closes`, `closed`, `resolve`, `resolves`, `resolved`) anywhere in the PR title, body, or any commit message — regardless of context, formatting, code blocks, or quotes.

**Block the PR if any of these are true:**

- PR body / title / commits contain `<keyword> #N` where `N` is an issue number
- AND the diff does NOT contain a real source-code change that fixes that issue (i.e. only docs changes, only test changes, only refactor without behaviour change)

Run:

```bash
# Detect close keywords + issue numbers
git log origin/$BASE_BRANCH..HEAD --format="%B" | grep -niE "(fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)[[:space:]]*#[0-9]+"
gh pr view --json title,body --jq '.title + "\n" + .body' 2>/dev/null | grep -niE "(fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)[[:space:]]*#[0-9]+"

# Detect diff scope — is this only docs / tests / non-code?
git diff origin/$BASE_BRANCH...HEAD --stat | tail -3
git diff origin/$BASE_BRANCH...HEAD --name-only | grep -vE '\.(md|txt)$|^docs/|^\.github/' | head -20
```

If keyword + issue number found AND diff is docs/test/refactor only → BLOCK with message:

> 🛑 PR contains close keyword + issue number but diff has no source fix. GitHub will silently auto-close issue #N on merge. Replace with `Refs #N` / `Tracks #N`, or rephrase to avoid the keyword next to a number entirely (even inside backticks or quotes — the parser ignores formatting).

This is a hard gate. The repo has burned issues this way before (PSLE Alex #212/#213/#214 closed by docs-only PRs #215/#221/#222/#223 across 5/4 — none shipped code, all closed real production bugs by accident).

### B. Code Review Dimensions

**Correctness & Bugs**

- Logic errors, off-by-one, null/undefined access
- Race conditions in async, missing await on Promises
- Edge cases: empty arrays, null values, boundary conditions

**AI Anti-Patterns**

- Duplicated component that already exists in `src/components/`
- Copy-pasted logic that should be extracted to util/hook
- Business logic in UI component (should be in hook/service)
- Prop drilling that should use context/store

**Architecture & DRY**

- New file that duplicates existing module's responsibility
- Missing abstraction layer (direct DB calls from route handler)

**Performance**

- N+1 queries in loops
- Missing pagination on list endpoints
- Unbounded data fetching (no limit/offset)
- Large objects in React state causing re-renders

**Observability**

- New error paths without logging
- Silent failures (catch blocks that don't log)

### C. Confidence Scoring

Rate each finding 0-100:

- **0-25**: False positive or nitpick
- **25-50**: Possible issue, needs verification
- **50-75**: Probable issue, worth fixing
- **75-100**: Confirmed, must fix before merge

Only report findings scored **≥ 50**.

---

## Phase 2: SUBMIT

### Test Report (MANDATORY)

```bash
npx playwright test --reporter=json 2>&1
# or
npx vitest run --reporter=json 2>&1
```

Never say "tests pass" without this structured report:

```markdown
## Test Results

| Test File    | Pass  | Fail  | Total |
| ------------ | ----- | ----- | ----- |
| auth.spec.ts | 12    | 0     | 12    |
| **Total**    | **N** | **N** | **N** |

## All Test Cases

✅ Feature › test case name
❌ Feature › test case name (reason: ...)

## Coverage Analysis

| Feature Changed in PR | Tested? | Test Case             |
| --------------------- | ------- | --------------------- |
| New login flow        | ✅      | auth › user can login |
| New API route /users  | ❌      | NOT TESTED            |

## Missing Coverage

1. Feature X has no test
2. Error case Y not covered
```

### PR/MR Description

```markdown
## Summary

{1-3 bullet points of what changed and why}

## Changes

- `path/to/file.ts` — What was changed

## Test Results

{N pass, N fail}

## Checklist

- [ ] Tests pass
- [ ] No console.log / debug code
- [ ] No `any` types introduced
- [ ] API calls use shared client
- [ ] New routes have auth middleware
- [ ] Project conventions followed
- [ ] Changelog updated (if applicable)
```

### Create PR/MR

**GitHub:**

```bash
gh pr create --title "feat: description" --body "..." --base $BASE_BRANCH
```

**GitLab:**

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  "$GITLAB_API/projects/$GITLAB_PROJECT/merge_requests" \
  -d '{
    "source_branch": "'$BRANCH'",
    "target_branch": "'$BASE_BRANCH'",
    "title": "feat: description",
    "description": "...",
    "squash": true,
    "remove_source_branch": true
  }'
```

---

## Review Comment Tags

When posting review comments, prefix with a tag to indicate severity:

| Tag            | Meaning                    | Blocks merge |
| -------------- | -------------------------- | ------------ |
| `[blocker]`    | Must fix before merge      | ✅           |
| `[suggestion]` | Recommended, not required  | ❌           |
| `[question]`   | Needs author's explanation | ❌           |
| `[nit]`        | Minor style/naming issue   | ❌           |
| `[praise]`     | Good pattern worth noting  | ❌           |

Format:

```
[blocker] ComponentName: `any` type on line 23

Should use `OrderStatus` type. See project coding standards.

Suggested fix:
- const status: any = order.status
+ const status: OrderStatus = order.status
```

---

## Output: PR-REPORT.md

Write a single report combining both phases:

<!-- prettier-ignore -->
````markdown
# PR Report

**Branch**: {branch}
**Base**: {base}
**Date**: {date}
**Reviewer**: Claude Code (vcodes-pr)
**Platform**: GitHub / GitLab
**Files Changed**: {n}
**Lines**: +{added} -{removed}

## Verdict: READY ✅ / NOT READY ❌

## Gate Results

| Gate               | Status | Details |
| ------------------ | ------ | ------- |
| Clean tree         | ✅/❌  | ...     |
| Debug residue      | ✅/❌  | ...     |
| Type safety        | ✅/❌  | ...     |
| Security           | ✅/❌  | ...     |
| API client         | ✅/❌  | ...     |
| Project compliance | ✅/❌  | ...     |

## Code Review Findings

### [blocker] {Title} (confidence: {n}/100)

**File**: `path/to/file.ts:42`
**Category**: Bug / Security / Anti-Pattern / Architecture / Performance
**Evidence**:

\```diff
- problematic code
+ suggested fix
\```

### [suggestion] ...

### [nit] ...

## What Looks Good

- {Positive observations}

## Test Report

{Structured test report from Phase 2}

## PR Description (copy-paste ready)

{Generated PR/MR description}

## Blockers (if NOT READY)

1. [Gate N] description
2. [Finding] description
````

## Merge Strategy

1. Delete source branch after merge (GitHub: checkbox, GitLab: `remove_source_branch`)
2. Require at least 1 approval before merge
3. Choose merge method based on commit content:

| Scenario                                           | Method                               | Rationale                          |
| -------------------------------------------------- | ------------------------------------ | ---------------------------------- |
| All commits same type (all `feat:` or all `docs:`) | **Squash Merge**                     | Clean single commit                |
| Mixed types (`feat:` + `fix:` + `refactor:`)       | **Merge Commit** or **Rebase Merge** | Preserve distinct semantic commits |
| Single commit                                      | **Merge Commit**                     | Nothing to squash                  |
| Messy commits ("wip", "fix fix", "aaaa")           | **Squash Merge**                     | Clean up garbage history           |

4. When squashing: PR/MR title becomes the commit message — follow commit conventions
5. When not squashing: ensure every commit follows `type: description` format

## Rules

- Review the FULL diff, not just the latest commit
- Don't report issues on unchanged lines (pre-existing problems)
- Acknowledge good patterns — reviews shouldn't be all negative
- Don't auto-fix — report and let user decide
- Test report is mandatory — never skip
- Run ALL gates — don't skip even if user says "just submit"
- If user proceeds despite warnings, note it in PR/MR description
- GitHub: use `gh pr comment` to post findings
- GitLab: use API to post MR notes
- Never auto-merge or approve without explicit user instruction
- After READY verdict: suggest creating/updating PR/MR
