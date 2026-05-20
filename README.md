# FocusHub API

REST API for **FocusHub** — a team productivity and focus-tracking platform. Built with Django and designed for a modern React/Next.js client, with Firebase for social login and first-party JWT sessions for every API call.

Pair with the frontend: [`focushub-frontend`](../focushub-frontend)

---

## Why this project

FocusHub is a full-stack portfolio piece that goes beyond CRUD demos. It implements patterns you see in production SaaS products:

- **External identity + owned sessions** — Firebase proves who you are once; the API issues and controls its own tokens.
- **Multi-tenant workspaces** — data and permissions scoped per team, not per user globally.
- **Role-based access control** — owner / admin / member rules enforced in a dedicated permissions layer.
- **Invitation flows** — token-based invites with expiry, email matching, and idempotent accept/decline.
- **Revocable refresh tokens** — hashed at rest, rotated on refresh, revocable on logout or account delete.

The API is documented with OpenAPI and structured for clear separation of views, serializers, services, and domain logic.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Framework | **Django 5** |
| API | **Django REST Framework** |
| Database | **PostgreSQL** (Neon) |
| Auth (identity) | **Firebase Admin SDK** (Google / Apple ID tokens) |
| Auth (sessions) | **djangorestframework-simplejwt** + server-side refresh store |
| API docs | **drf-spectacular** (OpenAPI 3 + Swagger UI) |
| Config | **python-dotenv** |
| CORS | **django-cors-headers** |

---

## Features (implemented)

### Authentication & users

- `POST /api/v1/auth/firebase` — verify Firebase ID token, upsert user, return `{ access, refresh, user }`
- `POST /api/v1/auth/refresh` — rotate refresh token (old token revoked in DB)
- `POST /api/v1/auth/logout` — revoke current refresh token
- `GET/PATCH/DELETE /api/v1/users/me` — profile read/update and soft-delete (`is_active=false` + revoke all sessions)

Custom `User` model (UUID PK, `firebase_uid`, no password login). Refresh tokens stored as **SHA-256 hashes** with `jti` — raw tokens never persisted.

### Workspaces & RBAC

- Workspace CRUD with soft delete
- Members: list, change role (owner only), remove member or leave workspace
- Permissions: `owner` > `admin` > `member` with helpers like `require_min_role` and last-owner protection
- Non-members receive **404** on workspace routes (no existence leak)

### Invitations

- Create/list/revoke pending invites (owner/admin)
- Accept/decline via secure token URL (`/invitations/:token/accept|decline`)
- Email must match authenticated user; pending invites enforced with DB constraints

### Developer experience

- Interactive docs: **`/api/v1/docs/`** (Swagger UI)
- OpenAPI schema: **`/api/v1/schema/`**
- Function-based `@api_view` handlers grouped by domain (`views/auth.py`, `views/workspaces.py`, etc.)
- Service layer for multi-step flows (`create_workspace`, invitation lifecycle)

---

## Architecture

```text
Client (Next.js)
    │
    ├─► Firebase Auth  ──► ID token (login only)
    │
    └─► FocusHub API   ──► JWT access + refresh
              │
              ├─ users app     (auth, me, RefreshToken model)
              └─ workspaces app (Workspace, Member, Invitation, RBAC)
                        │
                        ▼
                 PostgreSQL (Neon)
```

**Request flow (authenticated):**

1. Client sends `Authorization: Bearer <access>`.
2. DRF `JWTAuthentication` validates access JWT.
3. View loads workspace membership and runs permission checks.
4. Serializer validates input; service layer handles transactions where needed.

---

## API overview

Base URL: `/api/v1/`

| Area | Endpoints |
|------|-----------|
| Auth | `POST auth/firebase`, `auth/refresh`, `auth/logout` |
| Users | `GET/PATCH/DELETE users/me` |
| Workspaces | `GET/POST workspaces`, `GET/PATCH/DELETE workspaces/:id` |
| Members | `GET workspaces/:id/members`, `PATCH/DELETE .../members/:userId` |
| Invitations | `GET/POST workspaces/:id/invitations`, `DELETE .../invitations/:id`, `POST invitations/:token/accept\|decline` |

Full spec (including planned endpoints): [`docs/api-v1.md`](docs/api-v1.md)

---

## Project structure

```text
focushub_backend/
├── config/                 # Django settings, root URLs, WSGI
├── apps/
│   ├── users/
│   │   ├── models.py       # User, RefreshToken
│   │   ├── tokens.py       # Issue, rotate, revoke JWT + DB rows
│   │   ├── firebase.py     # Firebase ID token verification
│   │   ├── services.py     # get_or_create_user_from_firebase
│   │   └── views/          # auth.py, me.py
│   └── workspaces/
│       ├── models.py       # Workspace, WorkspaceMember, WorkspaceInvitation
│       ├── permissions.py  # RBAC helpers
│       ├── services.py     # create_workspace, invitation logic
│       └── views/          # workspaces, members, invitations
├── docs/
│   ├── api-v1.md           # Endpoint specification
│   └── progress.md         # Implementation log
└── requirements.txt
```

---

## Quick start

### Prerequisites

- Python 3.11+
- PostgreSQL database (e.g. [Neon](https://neon.tech))
- Firebase project with Google (and optionally Apple) sign-in enabled
- Firebase **service account** JSON for the Admin SDK

### Setup

```bash
cd focushub_backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with Postgres + Firebase credentials
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/api/v1/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/v1/schema/ | OpenAPI schema |
| http://127.0.0.1:8000/admin/ | Django admin |

Create a superuser for admin (optional):

```bash
python manage.py createsuperuser
```

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `PGHOST` | PostgreSQL host |
| `PGDATABASE` | Database name |
| `PGUSER` | Database user |
| `PGPASSWORD` | Database password |
| `PGPORT` | Port (default `5432`) |
| `FIREBASE_CREDENTIALS` | Absolute path to Firebase service account JSON |
| `FRONTEND_URL` | Base URL for invite links (default `http://localhost:3000`) |

See [`.env.example`](.env.example). Never commit `.env` or credential files.

---

## Design highlights

**Custom user without passwords** — `AbstractBaseUser` + `PermissionsMixin`, `firebase_uid` as stable external identity, unusable password for normal users.

**Server-side session control** — Refresh tokens hashed with SHA-256; rotation revokes the previous row before issuing a new pair; logout and account deletion revoke tokens explicitly.

**Multi-tenant safety** — Workspace-scoped queries; membership required for all workspace routes; role checks centralized in `permissions.py` rather than duplicated in views.

**Soft deletes** — Users and workspaces use `is_active` so data can be retained without exposing deleted resources in list/detail endpoints.

**OpenAPI-first** — `@extend_schema` on views; schema and Swagger served from the same codebase as the implementation.

---

## Roadmap

Planned next (spec already in `docs/api-v1.md`):

- Tasks, tags, and task–tag associations (workspace-scoped)
- Focus sessions (server-tracked timers + stats)
- In-app notifications and activity logs
- Mock subscriptions and premium entitlements

---

## Related repos

- **Frontend:** Next.js 16, TanStack Query, Zustand, Firebase Web SDK, shadcn/ui — see `focushub-frontend`

---

## License

Private / portfolio use — add a license file if you open-source the repo.
