---
name: vcodes-qa
description: |
  QA testing with structured bug report. Runs Playwright E2E tests and manual
  verification. Records bugs only — NEVER fixes code. Outputs a markdown QA
  report with severity, screenshots, and repro steps. Use when asked to "QA",
  "test this", "find bugs", "run tests", "check for bugs", "QA report", or
  before any release/deployment. Also use when user says "does this work" or
  "is this ready".
allowed-tools: [Bash, Read, Grep, Glob, Write]
disable-model-invocation: false
---

# QA Testing

Record bugs only. NEVER modify source code. NEVER fix bugs.
Output a structured QA report.

Why no fixes: QA runs in worktrees or separate context. Fixing code here
creates merge conflicts with the development branch. Bugs get fixed in
the dev branch using the report as reference.

## Step 0 (BLOCKING): Read the project's test instructions FIRST

Before running any E2E test, look for a project-level test guide and READ IT:

```bash
# Look for a project-authored instructions file — MUST be read before running tests
ls tests/INSTRUCTIONS.md e2e/INSTRUCTIONS.md tests/README.md e2e/README.md 2>/dev/null
```

If any of these exist, read the file in full before proceeding. It will
document project-specific invariants the generic skill cannot know:

- How to invoke tests (projects / tags vs file paths)
- Auth setup: one-time login via `storageState`, never per-test
- Tier/entitlement chain (free / basic / premium — different projects)
- Which tags map to which setup project
- Local overlay-handling helpers
- Known banned patterns (e.g. `test.skip`, `{ force: true }`)

If `tests/INSTRUCTIONS.md` contradicts a generic rule below, the project
file wins.

## Process

1. **Read project test instructions** (Step 0 above) — BLOCKING
2. **Discover** — Read project structure, identify test files, key user flows
3. **Run existing tests** — Execute test suites (Playwright, Vitest, Jest, etc.), collect results
4. **Manual verification** — Test critical user flows via browser if available
5. **Record** — Write `QA-REPORT.md` with all findings
6. **Summary** — Print pass rate and critical bug count
7. **Process audit** — Kill orphan Chromium processes (see Process Hygiene)

## Test Framework Detection

Before running tests, detect the project's test setup:

```bash
# Check for test config files
ls vitest.config.* playwright.config.* jest.config.* .mocharc.* 2>/dev/null
# Check for test directories
ls -d test/ tests/ spec/ __tests__/ cypress/ e2e/ 2>/dev/null
# Check package.json for test scripts
grep -A2 '"test"' package.json 2>/dev/null
```

Adapt commands to the detected framework. Common patterns:

| Framework | Run all | Filter by tag/project (preferred) | Run single file (LAST RESORT) | JSON output |
|-----------|---------|-----------------------------------|--------------------------------|-------------|
| Playwright | `npx playwright test` | `npx playwright test --project=X --grep @tag` | `npx playwright test path/file.spec.ts` | `--reporter=json` |
| Vitest | `npx vitest run` | `npx vitest run -t "pattern"` | `npx vitest run path/file.test.ts` | `--reporter=json` |
| Jest | `npx jest` | `npx jest -t "pattern"` | `npx jest path/file.test.ts` | `--json` |

**Prefer tags/projects over file paths.** Playwright projects often have
sequential dependencies (auth-setup → tier-setup → tests). Running a raw
`.spec.ts` file bypasses those setup projects and produces false failures.
When the project has `INSTRUCTIONS.md`, follow its invocation guidance.

Parse JSON output for: test name, status (pass/fail/skip), duration, error message.

## E2E Discipline (applies to all Playwright runs)

1. **One-time auth** — if the config defines `storageState`, tests must reuse
   it. Never call `page.goto('/login')` inside a test body unless the test
   itself is about the login flow.
2. **Tier awareness** — if the project has `free` / `basic` / `premium`
   tiers (or similar entitlement groupings), every test must carry a tag
   placing it in the right project. A test that expects a paywall running
   under premium will false-fail. A test that expects full access running
   under free will false-fail. Read `INSTRUCTIONS.md` to learn the mapping.
3. **No `test.skip()`** — covered in the No Skip Rule section below.

## Process Hygiene

After every test run, audit for orphan browser processes:

```bash
ps aux | grep -iE "chromium|playwright" | grep -v grep
```

If > 5 orphans remain after a run has ended, kill them:

```bash
pkill -f "Chromium.*--type=renderer"
pkill -f "playwright test"
```

Never raise `workers` beyond the project default without reason. Never
spawn `chromium.launch()` in a helper — always use Playwright fixtures.

## Unit / Component Test Standards

When writing NEW unit or component tests:

### Structure

```typescript
describe('ModuleName', () => {
  const defaultInput = { /* typical input */ }

  it('describes expected behavior', () => {
    // Arrange → Act → Assert
  })
})
```

### Rules

1. Each `describe` maps to one module, component, or function
2. `it` describes behavior: "returns X when Y" / "renders X" / "calls Y when Z"
3. Prefer semantic queries: `getByRole` > `getByText` > `getByTestId`
4. Mock external dependencies (API, router, storage), not internals
5. Test user-observable behavior, not implementation details
6. Each test is independent — no shared mutable state, no execution order dependency
7. Define `defaultProps` / `defaultInput` at `describe` top level

### Coverage Principles

| Priority | What to test |
|----------|-------------|
| Must | Error handlers, business logic with conditionals, API boundaries |
| Should | Pure functions (all branches + edge cases), hooks (return values + state changes) |
| May skip | Third-party UI library internals, static config, trivial getters |

## Playwright E2E Standards

### Locator Priority (strict order)

1. `getByRole('button', { name: 'Submit' })` — BEST
2. `getByLabel('Email')` — form inputs
3. `getByText('Welcome')` — visible text
4. `getByPlaceholder('Search...')` — placeholder text
5. `getByTestId('user-card')` — explicit contract
6. CSS/XPath — NEVER USE

### Waiting

- NEVER `page.waitForTimeout(ms)` — #1 cause of flaky tests
- Use `await expect(locator).toBeVisible()` — auto-retries
- Use `await page.waitForLoadState('networkidle')`
- Just call the action — Playwright auto-waits for actionability

### Assertions (web-first, auto-retry)

```typescript
await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
await expect(page.getByRole('button', { name: 'Save' })).toBeEnabled()
await page.getByRole('button', { name: 'Save' }).click()

await expect(page.getByRole('alert')).toContainText('Saved')
await expect(page).toHaveURL('/dashboard')
```

### Disambiguation

Use `{ exact: true }` when text could match multiple elements:

```typescript
page.getByRole('button', { name: 'Next', exact: true })
```

### Extract Navigation Helpers

Repeated multi-step navigation → extract to helper function:

```typescript
async function navigateTo(page: Page, path: string) { ... }
```

### Anti-Patterns

| Bad | Good |
|-----|------|
| `page.waitForTimeout(2000)` | `expect(locator).toBeVisible()` |
| `page.locator('div.card > button')` | `page.getByRole('button', { name: '...' })` |
| `page.isVisible()` then if/else | `expect(locator).toBeVisible()` |
| `page.$('selector')` | `page.getByRole()` / `page.getByText()` |
| `body.textContent().includes()` | `expect(locator).toContainText()` |
| `.getAttribute('class').includes()` | `toHaveClass()` / `toBeChecked()` / `toHaveAttribute()` |
| Tests sharing state across test() | `beforeEach()` for setup |
| Ambiguous locator without exact | `{ exact: true }` when needed |
| `test.skip()` for any reason | `expect(precondition).toBe(true)` — fail loudly |
| `.click({ force: true })` to "bypass overlay" | dismiss the overlay or use proper locator |
| "Agentation blocks click" in report | re-read the error; blocker is always a product element, not the dev widget |

### Overlay Handling (critical)

Two overlay types. Treat them differently.

**Type A — One-time onboarding overlays** (PWA install banner, intro modals, XP celebration):
- Only show for fresh state (new user / cleared storage). A normal test user won't see them.
- They show in QA because `reset-user` wipes the dismissed-flags.
- Pattern: expect-may-show; dismiss if visible; proceed if not.
  ```ts
  const intro = page.getByRole('button', { name: "Got it, let's go!" })
  if (await intro.isVisible({ timeout: 1000 }).catch(() => false)) {
    await intro.click()
    await expect(intro).toBeHidden({ timeout: 2000 })
  }
  // proceed to real target
  await page.getByRole('button', { name: 'Take Exam' }).click()
  ```
- Centralize in `tests/helpers/overlay.ts` → `dismissOverlays(page)`; call once per navigation. Do NOT reimplement inline.

**Type B — Persistent dev-tool widgets** (Agentation annotation widget, Next.js Dev Tools, React Query devtools):
- Always present in dev; never dismiss.
- They do NOT hide DOM elements from `getByRole`/`getByText` — locators query the accessibility tree, not geometry.
- They do NOT intercept pointer events on other elements. If a click fails, the blocker is a product modal (Type A) or a locator bug — never the dev widget.
- Pattern: ignore. Just use `getByRole` + `.click()`.

**Forbidden in bug reports** (always wrong):
- "Agentation intercepts the click"
- "Agentation blocks page interactions"
- "dev widget covers the button"

The Playwright error log names the actual intercepting element by class (e.g. `<div class="fixed inset-0 z-50 bg-black/70"> intercepts pointer events`). Quote that class in the bug report. Fix THAT element, not the dev widget.

### No Skip Rule

- **`test.skip()` is banned** in this codebase. Every test must either pass or fail.
- A skipped precondition hides a broken flow: "Take Exam button not found" is a P0 bug, not a reason to skip.
- Replace every `if (!x) test.skip()` with `expect(x, 'x precondition failed').toBe(true)`.
- Replace every `test.skip(cond, 'reason')` with `expect(!cond, 'reason').toBe(true)` or `throw new Error('reason')`.

### Test Structure

```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: login, navigate, seed data
  })

  test('user can do X', async ({ page }) => {
    // Arrange: setup state
    // Act: perform user action
    // Assert: verify outcome
  })
})
```

### Naming

- Test names describe USER BEHAVIOR: "user can submit form"
- Not implementation: "form handler calls API"

### Independence

- Each test sets up its own state via `beforeEach`
- No test depends on another test's side effects
- Tests can run in any order, in parallel

## CI Integration Principles

1. All tests must pass before merge — no exceptions
2. Coverage target: core business logic > 80%
3. E2E covers all critical user flows
4. New features require tests; bug fixes require regression tests
5. Flaky tests are bugs — fix or quarantine, never ignore

## Report Format

Write to `QA-REPORT.md` in project root:

```markdown
# QA Report
**Project**: {name}
**Date**: {date}
**Tester**: Claude Code (vcodes-qa)
**Branch**: {branch}
**Commit**: {short sha}

## Summary
| Metric          | Value    |
|-----------------|----------|
| Tests Run       | n        |
| Passed          | n (n%)   |
| Failed          | n (n%)   |
| Skipped         | n        |
| Critical Bugs   | n        |
| High Bugs       | n        |
| Medium Bugs     | n        |
| Low Bugs        | n        |

## Test Results
| Test | Status | Duration | Error |
|------|--------|----------|-------|
| ... | PASS/FAIL | 1.2s | error message if failed |

## Bugs Found

### [BUG-001] {Title}
**Severity**: CRITICAL / HIGH / MEDIUM / LOW
**Category**: Auth / UI / Data / Performance / UX
**Page/Route**: `/path`
**Steps to Reproduce**:
1. Go to ...
2. Click ...
3. Observe ...
**Expected**: What should happen
**Actual**: What actually happens
**Evidence**: Error message, screenshot path, or console output
**Test File**: `tests/xxx.spec.ts:42` (if from test failure)

### [BUG-002] ...

## Test Coverage Gaps
- [ ] Flows not covered by existing tests
- [ ] Edge cases not tested
- [ ] Missing error state tests

## Recommendations
- Priority fixes (CRITICAL/HIGH bugs)
- Test improvements needed
```

## Rules

- NEVER edit source code, components, API routes, or config files
- NEVER fix bugs — only record them
- NEVER modify existing test files to make them pass
- You MAY write NEW test files if asked to expand test coverage
- Every bug must have: severity, repro steps, expected vs actual
- Parse test output programmatically — don't summarize from memory
- Include commit SHA and branch in report for traceability
