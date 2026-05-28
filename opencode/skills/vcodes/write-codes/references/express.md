# Express / Node.js Backend Standards

## Project Structure
```
src/
├── app.ts              ← Express app setup + middleware
├── server.ts           ← Listen (separate from app for testing)
├── routes/
│   ├── index.ts        ← Route registration
│   ├── users.ts        ← /api/users routes
│   └── auth.ts         ← /api/auth routes
├── middleware/
│   ├── auth.ts         ← JWT/session validation
│   ├── validate.ts     ← Request validation (zod)
│   ├── rateLimiter.ts  ← Rate limiting
│   ├── errorHandler.ts ← Global error handler
│   └── logger.ts       ← Request logging
├── services/           ← Business logic (not in routes)
├── models/             ← DB models / schemas
├── types/              ← Shared TypeScript types
└── utils/              ← Helpers
```

## Middleware Order (CRITICAL)
```typescript
// app.ts — order matters
app.use(cors(corsOptions));
app.use(helmet());               // 1. Security headers
app.use(express.json());         // 2. Body parsing
app.use(requestLogger());        // 3. Log every request
app.use(rateLimiter());          // 4. Rate limiting
app.use('/api/auth', authRoutes); // 5. Public routes (no auth)
app.use(authMiddleware());       // 6. Auth (before protected routes)
app.use('/api', protectedRoutes); // 7. Protected routes
app.use(errorHandler());         // 8. Error handler (ALWAYS LAST)
```

## Auth Middleware
```typescript
// middleware/auth.ts
export const requireAuth = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Missing token' });

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!);
    req.user = payload as UserPayload;
    next();
  } catch {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

export const requireAdmin = (req: Request, res: Response, next: NextFunction) => {
  if (req.user?.role !== 'admin') {
    return res.status(403).json({ error: 'Admin required' });
  }
  next();
};
```

## Request Validation
```typescript
// middleware/validate.ts
import { z, ZodSchema } from 'zod';

export const validate = (schema: ZodSchema) =>
  (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: 'Validation failed',
        details: result.error.flatten().fieldErrors,
      });
    }
    req.body = result.data;
    next();
  };

// Usage in route:
const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

router.post('/users', validate(createUserSchema), createUser);
```

## Error Handling
```typescript
// middleware/errorHandler.ts
export class AppError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
  }
}

export const errorHandler = (err: Error, req: Request, res: Response, next: NextFunction) => {
  const status = err instanceof AppError ? err.statusCode : 500;
  const message = status === 500 ? 'Internal server error' : err.message;

  logger.error({
    method: req.method,
    path: req.path,
    status,
    error: err.message,
    stack: process.env.NODE_ENV !== 'production' ? err.stack : undefined,
  });

  res.status(status).json({ error: message });
};
```
- Never send stack traces in production
- Use custom `AppError` class with status codes
- Log full error server-side, send safe message to client

## Structured Logging
```typescript
// middleware/logger.ts
export const requestLogger = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  const requestId = crypto.randomUUID();
  req.requestId = requestId;

  res.on('finish', () => {
    logger.info({
      requestId,
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration: Date.now() - start,
      userId: req.user?.id,
    });
  });

  next();
};
```
- JSON format (not string concatenation)
- Include: requestId, method, path, status, duration, userId
- Redact sensitive fields: password, token, creditCard

## Route Patterns
```typescript
// routes/users.ts
const router = Router();

// List with pagination
router.get('/', async (req, res, next) => {
  try {
    const { page = 1, limit = 20 } = req.query;
    const users = await userService.list({ page: +page, limit: +limit });
    res.json({ data: users });
  } catch (err) {
    next(err); // Forward to error handler
  }
});
```
- Always forward errors with `next(err)`
- Use service layer for business logic (not in route handler)
- Paginate all list endpoints
- Return consistent response shape: `{ data }` or `{ error }`

## Common Mistakes
- Business logic in route handlers (should be in services/)
- Missing `next(err)` in catch blocks (request hangs)
- Error handler not last in middleware chain
- Missing rate limiting on auth endpoints
- Trusting `req.body` without validation
- Using `console.log` instead of structured logger
- Not closing DB connections on process exit
