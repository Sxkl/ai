---
name: vcodes-write-codes
description: |
  Full-stack coding standards that prevent common AI anti-patterns. Enforces
  DRY principles, component reuse, shared API clients with interceptors,
  centralized middleware, proper error handling, type safety, and test
  coverage. Use when writing any code, implementing features, or when asked
  to "write code", "implement", "build", "code this", "add feature", or
  any coding task. Also auto-trigger when generating frontend components,
  API routes, or backend logic.
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

# Write Codes

Before writing ANY code, run discovery. After writing, run verification.

> ## cube-new project specifics — apply these as well
>
> Full rules: `docs/refactor/14-coding-standards.md`. Quick rules every code change must obey:
>
> - **Stack**: React 18 + TS strict, Vite 6, AntD 5 + shadcn/ui + Tailwind 4, Zustand, TanStack Query, RHF + zod, react-router 7, react-i18next, Authing SDK, MSW, openapi-typescript.
> - **Folders**: `src/{app,api,features,components/{ui,domain,shared},stores,hooks,lib,styles,types,mocks,i18n,test}`. Each file lives in exactly one bucket.
> - **Boundaries (R2)**: features can NOT import from another feature. `lib/` is pure. UI primitives (`components/ui/*`) cannot reach into `api/`/`stores/`/`features/`.
> - **API (R5)**: only `src/api/*` imports axios/fetch. Everywhere else uses `@/api/modules/<domain>` hooks. Single client `src/api/client.ts` owns auth/tenant headers + retry + refresh.
> - **UI (R6)**: shadcn `@/components/ui/*` or AntD components only. No raw `<button>/<input>/<select>/<textarea>/<a>` in features/domain. New atom = PR + Design Lead approval. Icons: `lucide-react` only.
> - **Files (R3)**: ≤ 400 lines per file, ≤ 80 per function, complexity ≤ 12, depth ≤ 4. Split rather than nest.
> - **Types (R1)**: no `any`. Validate API in/out with `zod`. Branded types for IDs (`SimId` ≠ `OrderId`).
> - **Tests (R10)**: every change adds tests. Selectors: `getByRole`/`getByPlaceholder`/`getByLabel`/`getByText`. No `waitForTimeout`. ≥ 80% line on `src/{api,lib,stores,hooks}`.
> - **Naming**: PascalCase components, `useX.ts` hooks, lowercase utilities. **No** `*Helper.ts`/`*Utils.ts`/`*Manager.tsx`. **Named exports only** (no default exports for components).
> - **PR gate**: run `npm run pr:check` before requesting review. It runs lint + typecheck + tests + jscpd + build + feature-tagged e2e and writes `PR-REPORT.md`. The MR description must include the report.
> - **Old cube reference**: `/Users/meiyang/FrontEndProjects/cube/` for business logic only. Never sync code. Old API endpoints are additive — no semantic changes.
>
> Discovery checklist below still applies; treat the cube-new specifics as the additional layer.



## Stack-Specific References

After identifying the project's tech stack, read the relevant reference:
- Next.js App Router → [references/nextjs.md](references/nextjs.md)
- Express / Node.js backend → [references/express.md](references/express.md)
- Supabase (auth, DB, storage) → [references/supabase.md](references/supabase.md)

Read only what applies. Multiple may apply (e.g., Next.js + Supabase).

## Pre-Code Discovery (MANDATORY)

Before generating code, answer these:

1. **Existing patterns** — Grep codebase for similar logic. Reuse, don't recreate.
   ```bash
   # Find existing components, hooks, utils
   grep -r "export function\|export const\|export default" src/ --include="*.ts" --include="*.tsx" | head -40
   ```
2. **API client** — Does `src/api/`, `src/lib/api`, or similar exist? Use it.
3. **Component library** — Check `src/components/ui/` or design system. Use existing components.
4. **Shared hooks** — Check `src/hooks/`. Don't recreate `useAuth`, `useDebounce`, etc.
5. **Types** — Check `src/types/`. Extend existing types, don't duplicate.
6. **CLAUDE.md / design.md** — Re-read for project conventions.

## Frontend Rules

### HTTP Client (CRITICAL)
- NEVER use raw `fetch()`. Use the project's HTTP client (ky, axios, or custom wrapper).
- If no client exists, CREATE ONE FIRST in `src/lib/api-client.ts`:
  - Base URL from env var
  - Auth token injection via beforeRequest hook
  - 401 response → token refresh or redirect to login
  - Error response → structured error object
  - Content-Type header default
- All API calls go through this client. No exceptions.

```typescript
// Pattern: Shared API client with ky
import ky from 'ky';

export const api = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_URL,
  hooks: {
    beforeRequest: [(req) => {
      const token = getToken();
      if (token) req.headers.set('Authorization', `Bearer ${token}`);
    }],
    afterResponse: [async (_req, _opts, res) => {
      if (res.status === 401) await handleAuthError();
    }],
  },
});
```

### Component Reuse
- Before creating a component, search for existing ones with similar purpose
- Shared UI components live in `src/components/ui/` (or project equivalent)
- Page-specific components live in the page's directory
- If a component is used in 2+ pages, move to shared
- Use compound component pattern for complex UI (Form, Table, Dialog)
- Layouts: `src/layouts/` or `src/app/layout.tsx` — never duplicate header/sidebar/footer

### State Management
- Colocate state — don't lift unless shared
- Server state: use React Query / SWR, not manual useState+useEffect
- Form state: use react-hook-form, not manual onChange handlers
- Global state: use zustand/jotai stores, not prop drilling

### Styling
- Follow project's existing approach (Tailwind, CSS modules, styled-components)
- Extract repeated Tailwind classes into component variants (cva/class-variance-authority)
- Never inline long className strings — extract to `cn()` utility or variant

## Backend Rules

### API Route Structure
- Centralized auth middleware — not per-route auth checks
- Centralized error handler — not try-catch in every route
- Request validation middleware (zod, joi) — not manual field checks
- Structured response format: `{ data, error, meta }`

```typescript
// Pattern: Middleware ordering
app.use(cors());
app.use(helmet());          // Security headers
app.use(requestLogger());   // Structured logging
app.use(rateLimiter());     // Rate limiting
app.use(authMiddleware());  // Auth (before routes)
// ... routes ...
app.use(errorHandler());    // Error handler (LAST)
```

### Logging
- Structured JSON logs (not console.log strings)
- Include: timestamp, request ID, method, path, status, duration
- Sensitive data redaction (tokens, passwords, PII)
- Error logs: include stack trace, request context, user ID

### Database
- Parameterized queries only — never string concatenation
- Migrations via CLI tool (not manual SQL or REST API)
- Connection pooling configured
- Query result typing (not `any`)

## Shared Rules (Frontend + Backend)

### Type Safety
- No `any` type — use `unknown` with type guards
- Export shared types from `src/types/`
- Use discriminated unions for variant types
- Use `as const` for string literal types
- Zod schemas for runtime validation + type inference

### Error Handling
- Every try-catch: specific error types, not bare catch
- Distinguish retryable vs fatal errors
- Never swallow errors silently (catch + ignore)
- User-facing errors: friendly message. Logs: full detail.

### DRY Detection
- Function in 2+ files → extract to `src/utils/`
- Component in 2+ pages → extract to `src/components/`
- Hook pattern in 2+ components → extract to `src/hooks/`
- API call pattern repeated → extract to API client method
- Validation logic repeated → extract to shared validator

### Code Hygiene
- Remove unused imports after refactoring
- Delete `_old`, `_backup`, `_v2` files before committing
- No commented-out code blocks
- No `console.log` in production code (use logger)
- No hardcoded strings — use constants or env vars

## Post-Code Verification

After writing code, verify:

1. **No duplication** — Did you reuse existing patterns?
2. **API client** — All HTTP calls go through shared client?
3. **Error handling** — All async operations have error handling?
4. **Types** — No `any`? Types exported from central location?
5. **Tests** — Unit test for new logic? Integration test for new API?

## Test Coverage Requirements

- New utility function → unit test
- New API route → integration test (happy path + error cases + auth)
- New component with logic → component test
- Bug fix → regression test that reproduces the bug first
- Minimum: every public function/API endpoint has at least 1 test
