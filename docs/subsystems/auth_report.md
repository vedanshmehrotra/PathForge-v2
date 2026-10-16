# Supabase Authentication Integration — Report

## Architecture

PathForge uses **Supabase Auth** with **Google OAuth** as the identity provider.
The backend verifies Supabase JWTs on every protected request.

```
FRONTEND                          SUPABASE                      BACKEND (FastAPI)
─────────                         ────────                      ────────────────
[Sign in with Google] ──→  Google OAuth
                              │
                          Redirect to app
                         (#access_token)
                              │
supabase.auth.getSession() ──→  returns session
                              │
Access token in              │
Authorization: Bearer <jwt> ──→ verify_supabase_token(jwt)
                                   │
                               JWKS fetch
                              (cached 1st call)
                                   │
                              jose.jwt.decode(token, RS256)
                                   │
                              Extract: sub (supabase_id), email
                                   │
                              _ensure_local_user(payload)
                                   │
                              ┌────┴────┐
                              │ EXISTS? │
                              └────┬────┘
                             YES     NO
                              │      └──→ INSERT new user row
                              │
                         return VerifiedUser
                           {user_id, supabase_id, email}
```

## Backend Flow

### 1. Supabase Client (`pathforge/auth/supabase_client.py`)

- Initializes `supabase.create_client()` with project URL and anon key
- Singleton pattern — one client instance per process
- Config loaded from environment: `SUPABASE_URL`, `SUPABASE_ANON_KEY`

### 2. JWT Verification (`pathforge/auth/auth_middleware.py`)

The `get_current_user()` FastAPI dependency:

1. Extracts `Authorization: Bearer <token>` header
2. Calls `verify_supabase_token(token)` which:
   - Parses JWT header to extract `kid` (key ID)
   - Fetches JWKS from `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`
     (cached after first fetch)
   - Finds matching JWK by `kid`
   - Verifies token signature using RS256
   - Validates expiry, audience (`authenticated`)
3. Calls `_ensure_local_user(payload)` which:
   - Looks up `users.supabase_id` in local DB
   - If found → returns existing `user_id`
   - If not found → INSERT new user row with:
     - `username` = supabase_id
     - `email` = from JWT claim
     - `experience_level` = "beginner" (default)
     - `onboarding_complete` = 0
4. Returns `VerifiedUser(user_id, supabase_id, email)`

### 3. Auth Routes (`pathforge/api/auth_routes.py`)

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/auth/session` | GET | Yes | Verify token, return basic user info |
| `/auth/me` | GET | Yes | Return full user profile from DB |
| `/auth/profile` | GET | Yes | Return topic profiles + overall Elo |

All protected endpoints use `Depends(get_current_user)`.

### 4. Business Endpoints

The existing business endpoints (`/analyze`, `/gaps`, `/elo`, `/recommend`)
currently accept `user_id` in the request body. They can be migrated to use
the authenticated user from the JWT by adding `Depends(get_current_user)`.

## Database Changes

### users table — added `supabase_id` column

```sql
ALTER TABLE users ADD COLUMN supabase_id TEXT UNIQUE;
```

- `supabase_id` stores the Supabase Auth user UUID (`sub` claim)
- Unique constraint prevents duplicate user records
- Schema.sql updated + migration in db.py

## Security

| Concern | Implementation |
|---------|---------------|
| Token verification | RS256 JWKS verification via `python-jose` |
| Expired tokens | `verify_exp=True` in `jose.jwt.decode()` |
| Malformed tokens | Caught by try/except, returns 401 |
| Missing tokens | Rejected with 401 by middleware |
| User identity | Always derived from verified JWT, never from request body |
| Auto-creation | New Supabase users get a local DB record on first login |
| No bypass | All auth routes check every request |

## Frontend Integration

The `google_login.js` module provides:

- `googleLogin()` — triggers Supabase `signInWithOAuth({ provider: "google" })`
- `handleSession()` — restores session on page load (checks URL hash + stored session)
- `getToken()` — returns current access token for API calls
- `signOut()` — calls `supabase.auth.signOut()`
- `googleLoginButton()` — creates a styled "Sign in with Google" button

### Usage

```javascript
import { googleLogin, handleSession, getToken } from './google_login.js';

// On page load
const session = await handleSession();
if (session) {
  const token = await getToken();
  // Use token in API calls
}

// On button click
document.getElementById("login-btn").onclick = googleLogin;
```

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| No Authorization header | 401 — Missing or invalid header |
| Empty token | 401 — Empty token |
| Malformed JWT | 401 — Malformed token header |
| Expired token | 401 — Invalid token (expired) |
| Invalid signature | 401 — Invalid token (signature mismatch) |
| Unknown Supabase user | Auto-creates local user record |
| Repeated first-time login | Idempotent — UNIQUE constraint on supabase_id |
| Network failure (JWKS fetch) | Propagates as 401 |

## Test Coverage

11 tests covering:
- Health endpoint still works
- All auth routes reject unauthenticated requests
- All auth routes reject fake/invalid tokens
- Bearer scheme validation
- Auth routes registered correctly
- Business endpoints remain accessible

## Files

| File | Purpose |
|------|---------|
| `pathforge/auth/__init__.py` | Package init |
| `pathforge/auth/supabase_client.py` | Supabase client singleton |
| `pathforge/auth/auth_middleware.py` | JWT verification + user mapping |
| `pathforge/auth/google_login.js` | Frontend Google login module |
| `pathforge/api/auth_routes.py` | `/auth/session`, `/auth/me`, `/auth/profile` |
| `pathforge/auth_test.py` | Authentication test suite |
| `pathforge/db/schema.sql` | Added `supabase_id` column to users |
| `pathforge/db/db.py` | Migration for `supabase_id` column |

## Future Improvements

- Add `Depends(get_current_user)` to business endpoints for JWT-authenticated user_id
- Implement refresh token rotation
- Add role-based access control (admin, user)
- Add rate limiting per authenticated user
- Implement session revocation (token blacklist)
- Add MFA support via Supabase
