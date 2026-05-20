# FocusHub — Progress & Learning Log

A living document tracking what we've built, what we've learned, and what's next.
Keep this open as a reference. Update after each significant milestone.

> **Companion docs:**
>
> - `[api-v1.md](./api-v1.md)` — locked-in endpoint spec

---

## Project Overview

**Goal:** Full-stack productivity / focus-tracking app, learning Django + DRF + Next.js along the way — with deliberate coverage of auth, multi-tenancy (workspaces), RBAC, subscriptions/entitlements, and common API patterns.

**Backend stack:**

- Django 5 + Django REST Framework
- PostgreSQL on Neon (cloud-hosted)
- Firebase Admin SDK (identity provider — Google/Apple sign-in)
- SimpleJWT (issue our own JWT after Firebase verifies identity)
- drf-spectacular (OpenAPI / Swagger at `/api/v1/docs/`)
- django-cors-headers (frontend on `localhost:3000`)

**Frontend stack** (`../focushub-frontend`):

- Next.js 16 (App Router, TypeScript, Turbopack)
- Tailwind v4 + shadcn/ui components
- Firebase Web SDK (Google / Apple sign-in popup)
- axios + Zustand (persisted auth) + TanStack Query
- Silent token refresh via axios interceptor

**Auth model:**
Firebase verifies identity once at login. Backend issues **our** access + refresh JWTs and stores refresh tokens **server-side** (`refresh_tokens` table) so sessions can be revoked and rotated.

---

## Backend Skills Map (what each step teaches)


| Skill                                     | Steps where you practice it |
| ----------------------------------------- | --------------------------- |
| Custom models, managers, migrations       | 1, 6–11                     |
| External identity (Firebase) + own JWT    | 2–4                         |
| Serializers, validation, OpenAPI          | 3–5, all API steps          |
| Service layer + `@transaction.atomic`     | 3, 6, 8, **11**             |
| Global vs object-level permissions (RBAC) | 5, **6**, 7, 10             |
| Soft delete + session revocation          | 5, 6, 8                     |
| Nested URLs + multi-tenant scoping        | 6–9                         |
| State machines / action endpoints         | 8–9                         |
| **Subscriptions, plans, entitlements**    | **11** (+ optional 12)      |
| Pagination, filtering, search             | 8–10                        |
| Audit / activity logs                     | 10                          |
| In-app notifications                      | 10                          |
| Webhooks & idempotency (real billing)     | 12 (optional, read-first)   |


---

## High-Level Roadmap


| Step | Title                                                           | Status   |
| ---- | --------------------------------------------------------------- | -------- |
| 1    | Custom User model + project structure                           | DONE     |
| 2    | Firebase Admin SDK setup                                        | DONE     |
| 3    | Firebase login endpoint                                         | DONE     |
| 4    | RefreshToken model + refresh / logout + frontend silent refresh | DONE     |
| 5    | `/api/v1/users/me` (get + update + soft delete)                 | DONE     |
| 6    | Workspaces + Members (RBAC)                                     | DONE     |
| 7    | Invitations                                                     | DONE     |
| 8    | Tasks + Tags + TaskTags (workspace-scoped; **no projects**)     | **NEXT** |
| 9    | Focus Sessions                                                  | UPCOMING |
| 10   | Notifications + Activity Logs                                   | UPCOMING |
| 11   | **Subscriptions (mock) + entitlements**                         | UPCOMING |
| 12   | Real billing primer (Stripe — optional, docs only)              | DEFERRED |


**Deferred (not blocking):**

- Step 4c: HttpOnly cookie for refresh token (security hardening)
- `POST /auth/logout-all`, `GET /auth/sessions`, `DELETE /auth/sessions/:id`
- `GET /api/v1/users/:id` (same-workspace public profile)

---

## Progress So Far

### Step 1 — Custom User model + project structure (DONE)

**What we built:**

- `apps/` folder layout; `apps/users` with custom `User` model.
- UUID PK, `firebase_uid`, `email`, `display_name`, `photo_url`, `is_premium`.
- `AUTH_USER_MODEL = "users.User"`; fresh Neon migration.

**Key learnings:** `AbstractBaseUser` + `PermissionsMixin`, custom `UserManager`, `set_unusable_password()` for Firebase users, Django platform tables vs app tables.

---

### Step 2 — Firebase Admin SDK setup (DONE)

**What we built:**

- `apps/users/firebase.py` — init + `verify_id_token()`
- `UsersConfig.ready()` startup hook
- Service account JSON outside repo; `FIREBASE_CREDENTIALS` in `.env`

---

### Step 3 — Firebase login endpoint (DONE)

**What we built:**

- `POST /api/v1/auth/firebase` — full chain: serializer → service → view → URLs
- Returns `{ access, refresh, user }`
- CORS enabled for `localhost:3000`
- End-to-end verified: Google sign-in → Neon `users` row → dashboard

**Files:** `serializers.py`, `services.py`, `views/auth.py`, `urls.py`, `config/urls.py`

---

### Step 4 — Server-side refresh tokens + refresh/logout + frontend (DONE)

**What we built (backend):**

1. `**RefreshToken` model** (`apps/users/models.py`)
  - `token_hash` (SHA-256, never store raw token)
  - `jti`, `is_revoked`, `expires_at`
  - FK to `User` with `related_name="refresh_tokens"`
2. `**apps/users/tokens.py`** — token utilities
  - `issue_token_pair(user)` — JWT + DB row
  - `rotate_refresh_token(raw)` — validate → revoke old → issue new pair
  - `revoke_refresh_token(raw)` — logout one session
  - `get_valid_stored_refresh_token(raw)` — JWT + DB checks
3. **Endpoints**
  - `POST /api/v1/auth/refresh` — rotation
  - `POST /api/v1/auth/logout` — revoke (204)
  - Login updated to use `issue_token_pair()` instead of stateless-only JWT
4. **Swagger** — `@extend_schema` on auth views so request bodies appear in `/api/v1/docs/`

**What we built (frontend):**

1. `**src/lib/api.ts`**
  - `refreshTokens(refresh)` → `POST /auth/refresh`
  - `revokeRefreshToken(refresh)` → `POST /auth/logout`
  - **Silent refresh interceptor:** on 401, call refresh once (deduped), update both tokens, retry original request; on failure → clear auth + reject
2. `**src/lib/auth-store.ts`** — added `setTokens()` for refresh-only updates
3. `**src/hooks/use-auth.ts**` — logout calls backend revoke before clearing local state

**Key learnings:**

- Refresh token rotation: each refresh revokes old token and issues new access + refresh
- Frontend must update **both** tokens after refresh
- Only one in-flight refresh at a time (`refreshPromise`) to avoid race conditions
- Auth paths (`/auth/*`) skip the 401-retry loop to prevent infinite refresh
- `AllowAny` on refresh/logout — token is in body, not `Authorization` header

**Verified:**

- Login creates row in `refresh_tokens`
- Postman refresh returns new pair; old refresh rejected after rotation
- Postman logout returns 204; refresh with same token fails
- Full-stack Google login → dashboard with user profile

---

### Step 5 — `/users/me` + profile UI (DONE)

**What we built (backend):**

1. `**UserMeUpdateSerializer`** — PATCH only `display_name`, `photo_url`
2. `**user_me**` in `views/me.py` — GET / PATCH / DELETE (`@api_view`)
3. `**revoke_all_refresh_tokens_for_user()**` — DELETE account revokes all sessions
4. `**firebase_login**` — rejects `is_active=False` users (`AuthenticationFailed`)
5. `**path("users/me", user_me)**` in `urls.py`

**What we built (frontend):**

1. `**getCurrentUser` / `updateCurrentUser` / `deleteCurrentUser`** in `api.ts`
2. `**AuthGuard**` — hydrates profile via GET `/users/me` before rendering protected pages
3. **Dashboard** — edit profile, delete account, logout unchanged

**Key learnings:**

- First **protected** endpoints using global `IsAuthenticated` + `request.user`
- Soft delete on `User` vs hard delete; login blocked after deactivate
- Separate serializers for **read** vs **write** shapes

---

## Full-Stack Auth Flow (current)

```text
[Sign in]
  Firebase popup → id_token
  → POST /api/v1/auth/firebase
  → { access, refresh, user } stored in Zustand/localStorage

[API requests]
  Authorization: Bearer <access>

[Access expired]
  401 → POST /api/v1/auth/refresh { refresh }
  → new { access, refresh } → retry original request

[Protected routes]
  AuthGuard → GET /users/me → sync user in Zustand

[Sign out]
  POST /api/v1/auth/logout { refresh }
  → Firebase signOut + clear localStorage → /sign-in

[Delete account]
  DELETE /users/me → revoke all refresh tokens → Firebase signOut → clear → /sign-in
```

---

## Domain Rules — Workspaces & Members (Step 6)

A **workspace** is the tenant boundary for **tasks**, tags, focus sessions, and activity. Users join via `**WorkspaceMember`** with a **role**. There is **no project layer** — tasks link directly to `workspace_id`.

### Roles


| Role       | Typical powers                                                                                        |
| ---------- | ----------------------------------------------------------------------------------------------------- |
| **owner**  | Create workspace (auto-assigned); PATCH/DELETE workspace; change roles; kick anyone except last owner |
| **admin**  | List members; kick **members**; send invites (Step 7); read activity log                              |
| **member** | Use workspace content; leave workspace                                                                |


### Membership rules (locked for implementation)

- **Create workspace:** `POST /workspaces` → workspace row + membership for `request.user` as `owner`.
- **List/retrieve:** only workspaces where user has an active membership and workspace `is_active=True`.
- **Not a member:** return **404** (do not leak workspace existence).
- **PATCH/DELETE workspace:** **owner only**; soft-delete workspace (`is_active=False`).
- **List members:** any member of the workspace.
- **PATCH member role:** **owner only** in v1 (`admin` ↔ `member`; no ownership transfer yet).
- **DELETE member:**
  - **Leave** (`userId == self`): allowed unless you are the **last owner**.
  - **Kick** (`userId != self`): owner can remove admin/member; admin can remove member only.
- **Invariant:** every active workspace has **≥ 1 owner**.

### How RBAC connects to later features


| Feature                       | Gate                           |
| ----------------------------- | ------------------------------ |
| Tasks / tags / focus sessions | member+                        |
| Invitations (Step 7)          | admin+ or owner                |
| Activity log (Step 10)        | admin+ or owner                |
| `GET /users/:id`              | same workspace, limited fields |


**New app:** `apps/workspaces/` — models, `permissions.py` helpers, `views/workspaces.py`, `views/members.py`.

---

## Domain Rules — Subscriptions (Step 11)

Tutorial billing is **mock** (no Stripe/RevenueCat) per `api-v1.md`, but structured like production so you learn subscriptions properly.

### Concepts you will learn


| Concept                 | What we do in FocusHub                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------- |
| **Plan**                | `free` vs `premium` (enum on `Subscription`)                                           |
| **Subscription record** | Source of truth: status, period dates, cancel timestamp                                |
| **Denormalized flag**   | `User.is_premium` — fast checks; updated in **service layer** with subscription        |
| **Entitlements**        | Python helpers / DRF permission: `require_premium`, `can_create_workspace`, etc.       |
| **Lifecycle**           | `active` → `canceled` (access until `current_period_end` or immediate — pick one rule) |
| **Idempotent upgrade**  | Upgrading when already premium returns current subscription, no duplicate rows         |
| **Audit**               | Subscription changes logged to activity or a simple history table (optional)           |


### API (from `api-v1.md`)

```text
GET    /api/v1/subscriptions/me
POST   /api/v1/subscriptions/me/upgrade     { "plan": "premium" }
POST   /api/v1/subscriptions/me/cancel
```

### Suggested data model (`apps/billing/` or `apps/subscriptions/`)

```text
Subscription
  - user (OneToOne or FK — OneToOne for tutorial)
  - plan: free | premium
  - status: active | canceled | trialing (trialing optional for teaching)
  - current_period_start, current_period_end
  - canceled_at (nullable)
  - created_at, updated_at
```

### Business rules (locked for Step 11)

1. Every user has exactly one **current** subscription row (create `free` on first login or lazily on first `GET /subscriptions/me`).
2. **Upgrade:** set `plan=premium`, `status=active`, set period end (e.g. +30 days mock), set `user.is_premium=True` in same transaction.
3. **Cancel:** set `status=canceled`, `canceled_at=now`; **tutorial choice:** premium access ends **immediately** (`is_premium=False`) — simpler than grace period; document in code.
4. **Entitlement examples** to wire after subscription works:
  - Free: max **1** workspace, basic focus stats and only 3 tasks per that person
  - Premium: unlimited workspaces (or higher cap), full stats export, priority badge in UI
5. Gate at **service layer** (raise `PermissionDenied`) and optionally DRF `IsPremium` permission class.

### Frontend (Step 11)

- Billing card on dashboard: current plan, Upgrade / Cancel buttons
- Show `is_premium` badge (already on dashboard)
- Handle `403` with “Upgrade to premium” toast

### Step 12 — Real billing (optional, learn without building)

Read-only study topics for later (not in v1 scope):

- Stripe Checkout vs Billing Portal
- Webhooks (`checkout.session.completed`, `customer.subscription.deleted`)
- Webhook signature verification + **idempotency keys**
- Never trust client-only payment success — server confirms via webhook
- Mapping `stripe_customer_id` / `subscription_id` on `Subscription` model

---

### Step 6 — Workspaces + Members (DONE)

**What we built:**

- `apps/workspaces/` — `Workspace`, `WorkspaceMember`, RBAC helpers, `create_workspace()` service
- Endpoints: list/create/detail workspace; list/PATCH/DELETE members
- Wired under `api/v1/`; optional Django admin registration

**Frontend:** dashboard `WorkspaceSection` — list/create/select workspace; `currentWorkspaceId` persisted in Zustand; TanStack Query for `GET /workspaces`.

---

### Step 7 — Invitations (DONE)

**What we built (backend):**

- **`WorkspaceInvitation` model** — email, role, `token`, `status`, `expires_at`, FK to workspace + `invited_by`
- **Partial unique constraint** — one pending invite per `(workspace, email)`
- **`services.py`** — `create_invitation`, `get_valid_pending_invitation`, `accept_invitation`, `decline_invitation`, `revoke_invitation` (`@transaction.atomic` on accept)
- **`views/invitations.py`** — nested + token routes; admin+ for list/create/revoke
- **`InvitationSerializer`** — includes `invite_url` (tutorial: no SMTP)

**What we built (frontend):**

- **`InvitationSection`** on dashboard (owner/admin only) — send invite, list pending, copy link, revoke
- **`/invitations/[token]`** — accept/decline; `AuthGuard` + `?next=` redirect through sign-in
- TanStack Query keys: `["workspaces", id, "invitations"]`

#### Django / DRF concepts you practiced (Step 7)

| Concept | Where in FocusHub |
|--------|-------------------|
| **ORM FK + related_name** | `workspace.invitations`, `user.sent_workspace_invitations` |
| **TextChoices / enums** | `InvitationStatus`, `WorkspaceRole` |
| **Partial `UniqueConstraint`** | Only one pending invite per email per workspace |
| **Service layer** | Views call `create_invitation()`; business rules not duplicated in views |
| **`transaction.atomic`** | Accept = create `WorkspaceMember` + update invite in one DB transaction |
| **Object-level permissions** | `require_min_role(ADMIN)` — not global `IsAdminUser` |
| **404 vs 403** | Not a workspace member → 404; wrong email on accept → 403 |
| **Nested URLs** | `/workspaces/:id/invitations` vs top-level `/invitations/:token/accept` |
| **SerializerMethodField** | `invite_url` built from `settings.FRONTEND_URL` |
| **DRF `ValidationError` / `PermissionDenied`** | Raised in services; DRF maps to 400/403 JSON |

**Verified flow:** Owner POST invite → copy `invite_url` → invitee signs in (same email) → POST accept → `GET /workspaces` shows new workspace.

---

## What's Next — Step 8: Tasks (workspace-scoped)

`Task` model with **`workspace` FK** (no projects). See `api-v1.md` §6.

**You will learn:** more ORM (filtering, status field), action endpoints (`POST /tasks/:id/complete`), scoping every query to `workspace_id` + membership check.

---

## Current Project Structure

### View layer convention (Option B)

HTTP handlers use `**@api_view` function-based views** in `apps/<app>/views/`, split by feature:

```text
apps/users/views/
├── __init__.py    # re-exports for urls.py
├── auth.py        # firebase_login, auth_refresh, auth_logout
└── me.py          # users/me (Step 5)
```

- **Public auth routes:** `@authentication_classes([])` + `@permission_classes([AllowAny])`
- **Protected routes:** rely on global `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` (no decorators needed)
- **URLs:** import callables directly — `path("auth/firebase", firebase_login)` (not `.as_view()`)

### Backend (`focushub_backend/`)

```text
focushub_backend/
├── apps/
│   ├── users/                  # DONE (auth + profile)
│   │   ├── models.py           # User + RefreshToken
│   │   ├── tokens.py
│   │   └── views/              # auth.py, me.py
│   ├── workspaces/             # DONE (Steps 6–7)
│   │   ├── models.py           # Workspace, Member, Invitation
│   │   ├── permissions.py
│   │   ├── services.py
│   │   └── views/              # workspaces, members, invitations
│   ├── tasks/                  # Step 8 (planned) — Task FK → Workspace
│   └── billing/                # Step 11 (planned)
│       ├── models.py           # Subscription
│       ├── services.py         # upgrade, cancel, entitlements
│       └── views/
├── config/
│   ├── settings.py             # CORS, AUTH_USER_MODEL, REST_FRAMEWORK
│   └── urls.py
├── docs/
│   ├── api-v1.md
│   └── progress.md
└── requirements.txt
```

### Frontend (`focushub-frontend/`)

```text
focushub-frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx            # landing
│   │   ├── sign-in/page.tsx    # ?next= redirect
│   │   ├── dashboard/page.tsx
│   │   └── invitations/[token]/page.tsx
│   ├── components/
│   │   ├── auth-guard.tsx
│   │   ├── workspace-section.tsx
│   │   └── invitation-section.tsx
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   ├── use-workspaces.ts
│   │   └── use-invitations.ts
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth-store.ts
│   │   ├── workspace-store.ts
│   │   └── firebase.ts
│   └── types/
│       └── api.ts
└── .env.local                  # Firebase Web + API_URL
```

---

## Quick Reference — Commands

### Backend

```bash
cd focushub_backend
source venv/bin/activate
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py runserver          # :8000
```

### Frontend

```bash
cd focushub-frontend
npm run dev                         # :3000
```

### URLs


| URL                                                                                      | Purpose                  |
| ---------------------------------------------------------------------------------------- | ------------------------ |
| [http://localhost:3000](http://localhost:3000)                                           | Frontend                 |
| [http://127.0.0.1:8000/api/v1/docs/](http://127.0.0.1:8000/api/v1/docs/)                 | Swagger                  |
| [http://127.0.0.1:8000/api/v1/auth/firebase](http://127.0.0.1:8000/api/v1/auth/firebase) | Login                    |
| [http://127.0.0.1:8000/api/v1/auth/refresh](http://127.0.0.1:8000/api/v1/auth/refresh)   | Refresh                  |
| [http://127.0.0.1:8000/api/v1/auth/logout](http://127.0.0.1:8000/api/v1/auth/logout)     | Logout                   |
| [http://127.0.0.1:8000/api/v1/users/me](http://127.0.0.1:8000/api/v1/users/me)           | Profile GET/PATCH/DELETE |
| http://localhost:3000/invitations/\<token\>                                               | Accept invite (frontend) |


---

## Remaining vertical slices


| Step | Backend focus                       | Notes                                              |
| ---- | ----------------------------------- | -------------------------------------------------- |
| 8    | **Tasks + tags** (workspace-scoped) | `Task.workspace` FK; no Project model              |
| 9    | Focus sessions                      | `task_id` → workspace; premium stats               |
| 10   | Notifications, activity             | Activity: admin/owner only                         |
| 11   | Mock subscriptions                  | Plans, upgrade/cancel, `is_premium`, feature gates |
| 12   | Stripe primer (docs)                | Webhooks, idempotency — no code required           |


### Simplified data model (no projects)

```text
User ──< WorkspaceMember >── Workspace ──< Task
                              └──< Tag ──< TaskTag >── Task
FocusSession ──> Task ──> Workspace
```

---

## Update Log


| Date       | Update                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------------------------- |
| 2026-05-19 | Initial backend setup: Django, DRF, Neon, JWT, spectacular.                                                             |
| 2026-05-19 | Step 1–2: custom User + Firebase Admin SDK.                                                                             |
| 2026-05-20 | API spec → `docs/api-v1.md`. Step 3: Firebase login endpoint.                                                           |
| 2026-05-20 | Next.js frontend scaffolded; Google sign-in E2E working.                                                                |
| 2026-05-20 | CORS added for frontend.                                                                                                |
| 2026-05-20 | **Step 4 complete:** RefreshToken model, refresh/logout APIs, Swagger schemas, frontend silent refresh + logout revoke. |
| 2026-05-20 | Created/updated `docs/progress.md`.                                                                                     |
| 2026-05-20 | Refactored HTTP layer to Option B: `views/auth.py` + `views/me.py` (`@api_view`), removed `api.py`.                     |
| 2026-05-20 | **Step 5 complete:** `/users/me` + frontend profile/edit/delete; inactive login blocked.                                |
| 2026-05-20 | Expanded plan: workspace RBAC rules, subscription/entitlements curriculum (Steps 12–13), backend skills map.            |
| 2026-05-20 | **Step 6 complete:** Workspaces + members API.                                                                          |
| 2026-05-20 | **Plan change:** Removed Projects layer; tasks scoped directly to workspaces (55 endpoints).                            |
| 2026-05-20 | **Step 7 complete:** Invitations backend (token, services, views) + frontend invite UI + accept page.                 |


