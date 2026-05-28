# Next.js Standards

## App Router

### File Conventions
- `page.tsx` — route page (server component by default)
- `layout.tsx` — shared layout (wraps children, persists across navigation)
- `loading.tsx` — loading UI (Suspense boundary)
- `error.tsx` — error boundary (`'use client'` required)
- `not-found.tsx` — 404 page
- `route.ts` — API route handler

### Server vs Client Components
- Default to Server Components — they fetch data, access DB, keep bundle small
- Add `'use client'` ONLY when needed: useState, useEffect, event handlers, browser APIs
- Never put `'use client'` on layout.tsx — wrap interactive parts in a client Providers component
- Pass server data to client components via props, not by fetching again on client

```typescript
// ✅ Server Component fetches, passes to client
// app/dashboard/page.tsx (server)
export default async function Page() {
  const data = await getData();
  return <DashboardClient data={data} />;
}

// ❌ Client component re-fetches
'use client'
export default function Page() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch('/api/data').then(...) }, []); // wasteful
}
```

### Data Fetching
- Server Components: `async/await` directly in component body
- Client Components: React Query / SWR (not raw useEffect + fetch)
- Server Actions: for mutations (form submissions, data updates)
- `revalidatePath()` / `revalidateTag()` for cache invalidation
- Never use `getServerSideProps` / `getStaticProps` (Pages Router patterns)

### API Routes (Route Handlers)
```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  // Auth check
  const user = await getUser(req);
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const data = await fetchData();
  return NextResponse.json({ data });
}
```

- Always validate auth in route handlers
- Use `NextRequest` / `NextResponse` types
- Return structured JSON: `{ data }` or `{ error }`
- Handle errors: wrap in try-catch, return appropriate status codes

### Middleware
```typescript
// middleware.ts (project root)
export function middleware(req: NextRequest) {
  // Runs on every matching route
  const token = req.cookies.get('token');
  if (!token) return NextResponse.redirect(new URL('/login', req.url));
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*'],
};
```
- Single `middleware.ts` at project root
- Use `matcher` to scope — don't run on static assets
- Keep thin: auth check, redirects, headers. No heavy logic.

### Environment Variables
- `NEXT_PUBLIC_*` — exposed to browser (public, non-secret)
- Everything else — server-only (secrets, API keys)
- Never put secrets in `NEXT_PUBLIC_*` variables
- Access via `process.env.VAR_NAME` (no import needed)

### Image & Font
- Use `next/image` for all images (auto-optimization)
- Use `next/font` for fonts (no layout shift, self-hosted)
- Never use raw `<img>` tags

### Common Mistakes
- Importing server-only code in client components (DB clients, secrets)
- Using `router.push()` for simple navigation (use `<Link>`)
- Missing `loading.tsx` causing blank screens during navigation
- Putting `'use client'` too high in the tree (makes children all client)
- Using `cookies()` or `headers()` without making component async
