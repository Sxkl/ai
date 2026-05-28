# Supabase Standards

## Client Setup

### Browser Client (Client Components)
```typescript
// src/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr';

export const createClient = () =>
  createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
```

### Server Client (Server Components / Route Handlers)
```typescript
// src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export const createClient = async () => {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
};
```

### Admin Client (Service Role — server-only)
```typescript
// src/lib/supabase/admin.ts
import { createClient } from '@supabase/supabase-js';

export const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY! // NEVER expose to client
);
```
- Service role key bypasses RLS — use only in trusted server code
- Never import admin client in client components
- Never put service role key in `NEXT_PUBLIC_*`

## Database

### Migrations (CRITICAL)
```bash
# Create migration
supabase migration new add_users_table

# Apply locally
supabase db reset

# Push to remote
supabase db push
```
- ALL schema changes via Supabase CLI migrations
- NEVER use Dashboard SQL editor or REST API for schema changes
- NEVER modify migration files after they've been applied
- One migration per logical change

### Row Level Security (RLS)
```sql
-- Always enable RLS on tables with user data
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can only read their own profile
CREATE POLICY "Users read own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = user_id);

-- Users can only update their own profile
CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = user_id);

-- Admin can read all
CREATE POLICY "Admin read all profiles"
  ON profiles FOR SELECT
  USING (auth.jwt() ->> 'role' = 'admin');
```
- Enable RLS on EVERY table that contains user data
- Test policies: try accessing data as wrong user
- Use `auth.uid()` for user-scoped access
- Use `auth.jwt()` for role-based access

### Typed Queries
```typescript
// Generate types from DB
// npx supabase gen types typescript --project-id <id> > src/types/database.ts

import { Database } from '@/types/database';

type Profile = Database['public']['Tables']['profiles']['Row'];
type InsertProfile = Database['public']['Tables']['profiles']['Insert'];

// Typed query
const { data, error } = await supabase
  .from('profiles')
  .select('*')
  .eq('user_id', userId)
  .single();
// data is typed as Profile | null
```
- Regenerate types after every migration: `supabase gen types typescript`
- Use generated types for all queries
- Never use `any` for query results

## Auth

### Auth Flow (Next.js App Router)
```typescript
// middleware.ts — refresh session on every request
import { createServerClient } from '@supabase/ssr';
import { NextResponse } from 'next/server';

export async function middleware(req) {
  const res = NextResponse.next();
  const supabase = createServerClient(url, key, {
    cookies: { /* get/set from req/res */ },
  });
  await supabase.auth.getUser(); // Refreshes session
  return res;
}
```

### Auth Patterns
```typescript
// Server Component — check auth
const { data: { user } } = await supabase.auth.getUser();
if (!user) redirect('/login');

// Route Handler — protect endpoint
export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  // ... handle request
}
```
- Always use `getUser()` (server-verified), not `getSession()` (can be spoofed)
- Protect every API route with auth check
- Use middleware to refresh sessions automatically

## Realtime
```typescript
// Subscribe to changes
const channel = supabase
  .channel('table-changes')
  .on('postgres_changes',
    { event: '*', schema: 'public', table: 'messages', filter: `room_id=eq.${roomId}` },
    (payload) => handleChange(payload)
  )
  .subscribe();

// Cleanup on unmount
return () => { supabase.removeChannel(channel); };
```
- Always unsubscribe on component unmount
- Use filters to scope subscriptions (don't listen to entire table)
- Enable realtime on specific tables in Dashboard

## Storage
```typescript
// Upload
const { data, error } = await supabase.storage
  .from('avatars')
  .upload(`${userId}/avatar.png`, file, {
    upsert: true,
    contentType: file.type,
  });

// Get public URL
const { data: { publicUrl } } = supabase.storage
  .from('avatars')
  .getPublicUrl(`${userId}/avatar.png`);
```
- Set storage policies (like RLS for files)
- Validate file type and size before upload
- Use user-scoped paths: `{userId}/filename`

## Common Mistakes
- Using `getSession()` instead of `getUser()` for auth verification
- Forgetting to enable RLS on new tables
- Modifying migration files after they've been applied
- Importing admin/service-role client in client components
- Not unsubscribing from realtime channels
- Using Dashboard SQL editor instead of CLI migrations
- Not regenerating types after schema changes
- Missing error handling on Supabase queries (ignoring `error` in `{ data, error }`)
