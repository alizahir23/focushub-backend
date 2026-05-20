# FocusHub API v1 — Endpoint Spec

**Base URL:** `/api/v1/`
**Auth:** Bearer JWT (`Authorization: Bearer <access_token>`), except auth endpoints and webhooks
**Conventions:**
- kebab-case URLs (`/focus-sessions`, not `/focusSessions`)
- Plural nouns (`/workspaces`, not `/workspace`)
- Action endpoints for state transitions (`POST /tasks/:id/complete`)
- Soft delete on user-facing resources (no destructive hard deletes)
- Common list params: `?page=&page_size=&ordering=&search=`

---

## 1. Auth

```
POST   /api/v1/auth/firebase            Verify Firebase ID token, return our { access, refresh, user }
POST   /api/v1/auth/refresh             Rotate refresh token, return new { access, refresh }
POST   /api/v1/auth/logout              Revoke current refresh token
POST   /api/v1/auth/logout-all          Revoke all refresh tokens for user
GET    /api/v1/auth/sessions            List active sessions (devices)
DELETE /api/v1/auth/sessions/:id        Revoke a specific session
```

## 2. Users

```
GET    /api/v1/users/me                 Current user
PATCH  /api/v1/users/me                 Update profile (display_name, photo_url)
DELETE /api/v1/users/me                 Soft delete: set is_active=false, revoke all sessions
GET    /api/v1/users/:id                Lookup user (same-workspace only, limited fields)
```

## 3. Workspaces

```
GET    /api/v1/workspaces               List workspaces I belong to
POST   /api/v1/workspaces               Create workspace (I become owner)
GET    /api/v1/workspaces/:id           Retrieve
PATCH  /api/v1/workspaces/:id           Update (owner only)
DELETE /api/v1/workspaces/:id           Soft delete (owner only)
```

## 4. Members

```
GET    /api/v1/workspaces/:id/members            List members
PATCH  /api/v1/workspaces/:id/members/:userId    Change role
DELETE /api/v1/workspaces/:id/members/:userId    Remove member / leave
```

## 5. Invitations

```
GET    /api/v1/workspaces/:id/invitations              List pending invites
POST   /api/v1/workspaces/:id/invitations              Send invite
DELETE /api/v1/workspaces/:id/invitations/:invId       Revoke invite
POST   /api/v1/invitations/:token/accept               Accept invite (token from email)
POST   /api/v1/invitations/:token/decline              Decline
```

## 6. Tasks

Tasks belong **directly to a workspace** (no project layer).

```
GET    /api/v1/workspaces/:id/tasks       List tasks in workspace
POST   /api/v1/workspaces/:id/tasks       Create task
GET    /api/v1/tasks/:id                  Retrieve
PATCH  /api/v1/tasks/:id                  Update (title, description, priority, due_date, status)
DELETE /api/v1/tasks/:id                  Soft delete
POST   /api/v1/tasks/:id/complete         Mark complete (sets completed_at, status='done')
POST   /api/v1/tasks/:id/reopen           Reopen (clears completed_at)
POST   /api/v1/tasks/:id/assign           Assign to a user  { "user_id": "..." }
```

**Task model (planned):** `workspace` FK, `title`, `description`, `status`, `priority`, `due_date`, `assignee` (nullable FK to User), `created_by`, soft-delete via `is_active`.

## 7. Tags

```
GET    /api/v1/workspaces/:id/tags      List tags (workspace-scoped)
POST   /api/v1/workspaces/:id/tags      Create
PATCH  /api/v1/tags/:id                 Update
DELETE /api/v1/tags/:id                 Delete
```

## 8. Task Tags

```
GET    /api/v1/tasks/:id/tags           List tags on a task
POST   /api/v1/tasks/:id/tags           Attach   { "tag_id": "..." }
DELETE /api/v1/tasks/:id/tags/:tagId    Detach
```

## 9. Focus Sessions (timer-style, server-tracked)

```
POST   /api/v1/focus-sessions/start         Start { "task_id": "..." } → returns session with id, started_at
POST   /api/v1/focus-sessions/:id/end       End session (computes duration_seconds)
GET    /api/v1/focus-sessions/active        Get current live session (if any)
GET    /api/v1/focus-sessions               List my sessions (?task_id=&from=&to=)
GET    /api/v1/focus-sessions/:id           Retrieve
DELETE /api/v1/focus-sessions/:id           Delete
GET    /api/v1/focus-sessions/stats         Aggregates: today, week, total
```

## 10. Subscriptions (mock — no third party)

```
GET    /api/v1/subscriptions/me              My subscription
POST   /api/v1/subscriptions/me/upgrade      Mock upgrade  { "plan": "premium" }
POST   /api/v1/subscriptions/me/cancel       Mock cancel
```

> Tutorial mode: no Stripe/RevenueCat in v1. Maintain a `Subscription` row (source of truth) and sync `User.is_premium` in the service layer on upgrade/cancel. Gate features via entitlements (workspace limits, premium stats). Full rules: `docs/progress.md` → **Domain Rules — Subscriptions**.

## 11. Notifications

```
GET    /api/v1/notifications                List mine (?unread=true)
PATCH  /api/v1/notifications/:id/read       Mark as read
POST   /api/v1/notifications/read-all       Mark all read
DELETE /api/v1/notifications/:id            Delete
```

## 12. Activity Logs

```
GET    /api/v1/workspaces/:id/activity      Workspace audit log (admin/owner)
```

## 13. Docs

```
GET    /api/v1/schema/                      OpenAPI schema (drf-spectacular)
GET    /api/v1/docs/                        Swagger UI
```

---

## Query parameter conventions

Standard params accepted on list endpoints:

| Param | Example | Meaning |
|---|---|---|
| `page` + `page_size` | `?page=2&page_size=20` | Pagination |
| `ordering` | `?ordering=-created_at` | Sort, `-` = descending |
| `search` | `?search=focus` | Free-text search |
| Field filters | `?status=open&priority=high` | Exact-value filter |
| Date ranges | `?from=2026-01-01&to=2026-02-01` | Range filter |

---

## Endpoint count summary

| Domain | Endpoints |
|---|---|
| Auth | 6 |
| Users | 4 |
| Workspaces | 5 |
| Members | 3 |
| Invitations | 5 |
| Tasks | 8 |
| Tags | 4 |
| Task Tags | 3 |
| Focus Sessions | 7 |
| Subscriptions (mock) | 3 |
| Notifications | 4 |
| Activity Logs | 1 |
| Docs | 2 |
| **Total** | **55** |

---

## Build order (vertical slices)

Each slice goes all the way: model → migration → serializer → service → view → URL → Postman test.

1. **Auth + Users** — DONE
2. Workspaces + Members (RBAC) — DONE
3. Invitations
4. **Tasks + Tags + TaskTags** (tasks scoped to workspace; no projects)
5. Focus Sessions
6. Notifications + Activity Logs
7. **Subscriptions (mock) + entitlements** — see `progress.md` for plan/rules
8. *(Optional)* Stripe / webhooks primer — docs only, not v1 code

---

## Design decisions locked in

| Decision | Choice |
|---|---|
| Version prefix | `/api/v1/` |
| User deletion | Soft delete (set `is_active=false`, revoke sessions) |
| State transitions | Dedicated action endpoints (`POST /complete`, `/reopen`) |
| Data hierarchy | **Workspace → Tasks** (no Project model) |
| Focus sessions | Timer-style, server-tracked |
| Billing | Mock only in v1 (no Stripe); `Subscription` row + `User.is_premium`; entitlements in service layer |
| Workspace RBAC | `owner` / `admin` / `member`; owner-only workspace PATCH/DELETE; see `progress.md` |
| Identity provider | Firebase (Google + Apple sign-in) |
| Session management | Server-side custom refresh tokens (not stateless JWT-only) |
