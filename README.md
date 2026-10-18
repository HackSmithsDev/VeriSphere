# VeriSphere

VeriSphere is a web platform for recording academic progress and student achievements. Students submit evidence, faculty review it, and students can share a portfolio containing verified work. Administrators manage accounts, curriculum, reports, and integrations.

The product is web-only. There is no native mobile application.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Configuration and secrets](#configuration-and-secrets)
- [Run with Docker Compose](#run-with-docker-compose)
- [Run locally](#run-locally)
- [Database and migrations](#database-and-migrations)
- [Backend API map](#backend-api-map)
- [Frontend map](#frontend-map)
- [Integrations and privacy](#integrations-and-privacy)
- [Validation](#validation)
- [Operations and troubleshooting](#operations-and-troubleshooting)
- [Scope and limitations](#scope-and-limitations)

## Features

- Student registration and sign-in, curriculum milestones, evidence uploads, and progress dashboards.
- Faculty review of milestones and activities; approval advances a student's learning path, while a revision request returns the item for updates.
- Administrator account management, faculty-to-course assignments, and student workbook imports with expiring password-setup invitations.
- Student achievements such as projects, certificates, courses, internships, volunteering, and competitions, with evidence links or files.
- Faculty-managed attendance and assessment marks, scoped to courses assigned by an administrator.
- Optional AI learning guidance and faculty feedback suggestions.
- Student-controlled portfolios and HTML resumes that contain verified items only. Students can create and revoke portfolio share links.
- Activity and academic reports, with CSV and XLSX exports.
- Optional faculty review email notifications, LinkedIn OpenID Connect, public GitHub profile statistics, and Redis caching.

## Architecture

```text
Browser
  └── React 19 / Vite frontend
       ├── Local development: Vite proxy → FastAPI
       └── Compose: Nginx → FastAPI
                         ├── PostgreSQL (Compose) or SQLite/PostgreSQL (local)
                         ├── Redis (optional cache; included in Compose)
                         ├── SMTP (optional email)
                         ├── Groq / Gemini (optional AI)
                         └── LinkedIn / GitHub (optional profile integrations)

Cloudflare Tunnel (optional Compose service) → configured frontend/API origins
```

The FastAPI application is under `backend/app`. Route modules call services for reusable business operations; SQLAlchemy models and Alembic migrations define persistence. The React SPA is under `frontend/src`, with API clients separated from screen components. Nginx serves the production frontend, forwards `/api/` and `/health` to the backend, and falls back to the SPA entry point for browser routes.

### Backend directories

| Path | Responsibility |
| --- | --- |
| `backend/app/api/v1/` | Versioned auth, student, faculty, administrator, activity, records, evidence, assistant, guest, and portfolio routes |
| `backend/app/core/` | Environment configuration, auth dependencies, security, database setup, logging, exceptions, course access, and startup lifecycle |
| `backend/app/db/models/` | SQLAlchemy entities and relationships |
| `backend/app/schemas/` | Request/response validation and API data shapes |
| `backend/app/services/ai/` | Provider selection, prompting, and feedback calibration |
| `backend/app/services/email/` | SMTP delivery and message templates |
| `backend/app/services/excel/` | Student workbook parsing/templates and XLSX report generation |
| `backend/app/services/portfolio/` | Verified-only portfolio assembly and HTML resume rendering |
| `backend/app/services/telemetry/` | GitHub public profile requests and LinkedIn OAuth |
| `backend/app/services/student_invitations.py` | Invitation token creation and account activation |
| `backend/app/utils/` | Shared helpers and optional Redis cache |
| `backend/alembic/` | Database migration environment and versioned schema changes |
| `backend/tests/` | Backend service and route integration tests |

### Frontend directories

| Path | Responsibility |
| --- | --- |
| `frontend/src/App.jsx` | Main SPA, role-aware navigation, sign-in, invitations, and workspace routing |
| `frontend/src/api/` | HTTP clients for authentication, admin, student, faculty, records, assistant, and evidence operations |
| `frontend/src/components/activities/` | Achievements, verified portfolios, integrations, and activity reports |
| `frontend/src/components/assistant/` | AI assistant and feedback controls |
| `frontend/src/components/records/` | Attendance, marks, and academic record interfaces |
| `frontend/src/components/evidence/` | Private evidence file retrieval |
| `frontend/src/components/ui/` | Shared buttons, badges, cards, and related UI elements |
| `frontend/src/App.css` | Application layout and component styling |

## Configuration and secrets

Never commit `.env` files, provider credentials, database passwords, tunnel tokens, or production signing keys. The checked-in `.env.example` files contain placeholders and safe public defaults only.

### Root `.env` (Docker Compose)

Copy the template, then replace the password placeholder with a generated value:

```sh
cp .env.example .env
openssl rand -hex 32
```

Use the generated password consistently in `POSTGRES_PASSWORD` and the password portion of `DATABASE_URL`. Use a URL-safe generated hex value so it does not need percent-encoding in the connection URL.

Root `.env` configures Compose infrastructure:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment; use `production` for the Compose deployment |
| `DEBUG` | Enables development reload when true; keep false for Compose |
| `WORKERS_COUNT` | API worker count; default to one for predictable startup seeding |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL container bootstrap credentials |
| `DATABASE_URL` | Backend connection to the Compose database host `postgres` |
| `CLOUDFLARED_TUNNEL_TOKEN` | Token for the named Cloudflare Tunnel, if running the tunnel service |

The tunnel token is obtained from Cloudflare for the named `verisphere` tunnel. The local credential JSON at `~/.cloudflared/verisphere.json` is sensitive; do not copy it into the repository or publish its contents. The ignored root `.env` may hold its derived tunnel token.

### `backend/.env` (API)

For local development, copy `backend/.env.example` to `backend/.env`. For Docker Compose, the same file supplies application settings; Compose overrides the database URL and internal host/port values while preserving the settings in this file.

| Variable group | Variables and purpose |
| --- | --- |
| Runtime | `APP_NAME`, `APP_ENV`, `HOST`, `PORT`, `DEBUG`, `WORKERS_COUNT` |
| Security | `SECRET_KEY` (generate with `openssl rand -hex 32`), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Storage and origins | `DATABASE_URL`, `REDIS_URL`, `UPLOAD_DIR`, `BACKEND_CORS_ORIGINS` |
| Initial administrator | `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`; set both or neither; the first password must be at least 12 characters |
| AI | `GROQ_API_KEY`, `GROQ_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`; either provider may be configured |
| Email | `MAIL_FROM`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM_NAME` |
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`, `LINKEDIN_SCOPES` |
| Student invitations | `FRONTEND_BASE_URL`, `STUDENT_INVITATION_EXPIRE_HOURS` |

LinkedIn credentials are optional and should stay blank until an approved LinkedIn application is configured. Register the callback URL exactly as the configured `LINKEDIN_REDIRECT_URI`. The public VeriSphere tunnel uses `https://verisphere-api.hacksmiths.dev/api/v1/student/telemetry/linkedin/callback`; the invitation page origin is `https://verisphere.hacksmiths.dev`.

The backend loads `backend/.env` first and then the repository root `.env`, without overriding values already in the process environment. Keep API-specific settings in `backend/.env`; the root file is for Compose interpolation.

### Frontend Vite environment files

Copy `frontend/.env.example` to `frontend/.env` for shared, non-secret frontend defaults. Vite uses mode-specific files when running a development server (`development`) or creating a production build (`production`). For a local backend override, use `frontend/.env.development.local`:

```dotenv
VITE_API_URL=http://127.0.0.1:8088/api/v1
VITE_APP_NAME=VeriSphere
```

This development-only file overrides `VITE_API_URL` from `frontend/.env` when running `npm run dev`. Do not name it `.env.local` if you want the local API override to apply only to development: `.env.local` is loaded for production builds too. Vite's precedence is: variables already present in the shell, `.env.[mode].local`, `.env.[mode]`, `.env.local`, then `.env`. Restart the Vite server after editing environment files.

For local development, you can instead set `VITE_API_URL=/api/v1`; Vite then proxies API requests to `127.0.0.1:8088` as configured in `vite.config.js`. The default `.env.example` uses this same-origin proxy path.

Production bundles use the production-mode/shared setting from `frontend/.env` unless overridden at build time. The Docker image excludes local `.env*` files and defaults to `/api/v1`; Nginx forwards that path to the backend. For a production frontend built separately and hosted on a different API domain, set HTTPS `VITE_API_URL` at build time and configure backend CORS accordingly. Every `VITE_*` variable is embedded in browser code and must never contain secrets.

## Run with Docker Compose

Prerequisites: Docker Engine/Desktop with Compose, root `.env`, and `backend/.env`.

```sh
cp .env.example .env
cp backend/.env.example backend/.env
# Set generated database credentials, DATABASE_URL, SECRET_KEY, and app settings.
# Add CLOUDFLARED_TUNNEL_TOKEN only if you want the tunnel container.
docker compose up --build
```

Compose runs PostgreSQL, Redis, the API, and the Nginx frontend. The Cloudflare connector is an opt-in profile. API startup applies Alembic migrations before starting FastAPI, then initializes the sample course and curriculum if the database is empty.

Local addresses:

- Frontend: <http://localhost:5176>
- API health: <http://localhost:8088/health>
- OpenAPI docs: <http://localhost:8088/docs>
- ReDoc: <http://localhost:8088/redoc>

The Cloudflare connector must use the published hostname/origin rules configured for the named tunnel. The connector being healthy does not by itself prove that Cloudflare DNS or public ingress routing is correct.

Useful commands:

```

The Cloudflare Tunnel is an opt-in Compose profile:

```sh
docker compose --profile tunnel up --build
```

Set `CLOUDFLARED_TUNNEL_TOKEN` in root `.env` before enabling that profile.sh
docker compose ps
docker compose logs -f backend
docker compose logs -f cloudflared
docker compose down
```

`docker compose down` preserves named database, Redis, and upload volumes. Do not use `docker compose down -v` unless you intentionally want to delete persisted data.

## Run locally

Use Python 3.13 and Node.js 22 or a compatible newer release.

```sh
cp backend/.env.example backend/.env
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python main.py
```

The local backend defaults should use a local SQLite URL and a locally generated `SECRET_KEY`. If you use PostgreSQL, set a local connection URL in `backend/.env`. Startup creates the sample curriculum when the database has no courses.

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

The Vite server listens on port 5176 and proxies `/api` and `/health` to `127.0.0.1:8088`. `npm run build` creates production assets; `npm run preview` serves that build for local smoke checks.

## Database and migrations

Migrations live under `backend/alembic/versions`. Use Alembic to upgrade an existing database:

```sh
cd backend
python -m alembic upgrade head
```

Always point `DATABASE_URL` at the intended database before running migrations. Compose migrates its PostgreSQL database automatically. `Base.metadata.create_all()` at API startup initializes missing schema objects and sample curriculum, but it does not replace migrations for changes to existing tables. Keep migrations in sync with model changes.

Persisted Compose volumes:

- `verisphere-postgres`: application database
- `verisphere-redis`: optional cache
- `verisphere-uploads`: private uploaded evidence
- `verisphere-data`: reserved application data

Back up the database and uploads before upgrades or volume maintenance.

## Backend API map

All versioned endpoints are prefixed by `/api/v1`. `/health` is an unversioned operational check.

| Route module | Main routes | Access |
| --- | --- | --- |
| `auth` | `/auth/register`, `/auth/login`, `/auth/me`, `/auth/invitations/accept` | Public registration/login; authenticated profile; invitation token for activation |
| `guest` | `/courses`, `/announcements` | Public |
| `student` | `/student/dashboard`, `/student/milestones`, milestone submissions, GitHub and LinkedIn profile flows | Student |
| `teacher` | Dashboard, milestone and activity review queues and review actions | Faculty; course assignments enforced |
| `admin` | Overview, users, courses, faculty accounts/assignments, workbook import/template, reports, feedback aggregates | Administrator |
| `activities` | Student activity list/create/update and faculty activity review | Student or assigned faculty |
| `records` | Student records; faculty academic options, attendance, and marks | Student, faculty, or administrator as appropriate |
| `evidence` | Upload/download private evidence and explicitly shared verified evidence | Owner/reviewer or valid share link |
| `portfolios` | Verified portfolio, resume, share-link enable/revoke, public portfolio/resume | Student for management; public for valid share token |
| `assistant` | Streaming chat and feedback | Authenticated role-specific access |

Interactive OpenAPI documentation at `/docs` is the authoritative source for request schemas, response formats, and status codes.

## Frontend map

The frontend is a React single-page application. `App.jsx` owns the role-aware workspace and invitation-acceptance route. API wrappers under `src/api` use `src/api/axios.js`; multipart workbook/evidence uploads use `FormData` and bearer authentication. `ActivityWorkspaces.jsx` hosts achievements, reports, verified portfolios, GitHub stats, and LinkedIn connection. `AcademicWorkspace.jsx` covers academic records. Shared controls are under `src/components/ui`.

For a production deployment on a separate API hostname, configure HTTPS `VITE_API_URL` at frontend build time and configure API CORS origins on the backend. The Compose/Nginx deployment instead uses the same-origin `/api/v1` proxy.

## Integrations and privacy

- **SMTP:** Review notifications and student invitations are sent only when SMTP is configured. Student import validates SMTP configuration before creating invitations. Delivery failures are logged; invitation tokens are stored hashed and expire according to `STUDENT_INVITATION_EXPIRE_HOURS`.
- **LinkedIn:** OpenID Connect starts only after a student action and provider consent. The callback state is signed and time-limited. VeriSphere stores the basic display name and HTTPS profile image URL; OAuth access tokens are not stored.
- **GitHub:** The authenticated student can request public profile statistics for a username. Only allowlisted public fields are returned. Redis caching is optional; GitHub is queried when the cache is unavailable.
- **AI:** Configure Groq, Gemini, or both. Groq is tried first, with Gemini as a fallback. Prompts include role-appropriate academic context. Do not send information to a provider unless your institution permits it.
- **Redis:** Used as an optional cache, not as the source of persistent application data.

## Validation

Run the backend suite:

```sh
cd backend
python -m pytest
```

Run frontend checks:

```sh
cd frontend
npm run lint
npm test
npm run build
```

Validate Compose configuration without starting services:

```sh
docker compose config --quiet
```

For a real deployment check, start Compose, verify all containers with `docker compose ps`, probe `/health`, open the frontend and `/docs`, then separately verify the public Cloudflare hostnames. OAuth, SMTP delivery, AI providers, and public tunnel behavior require valid external credentials/services and cannot be fully exercised with unit tests alone.

## Operations and troubleshooting

| Symptom | Checks |
| --- | --- |
| Compose reports a missing variable | Copy `.env.example` to root `.env`; fill database credentials, URL, and tunnel token if enabling Cloudflare |
| Backend cannot connect to PostgreSQL in Compose | Ensure `DATABASE_URL` uses host `postgres`, and its user/password/database match the `POSTGRES_*` variables |
| Alembic fails on startup | Check backend logs and DB readiness; confirm the configured database is reachable and the migration user can alter schema |
| Student invitation email is not received | Configure SMTP, check backend logs and spam filtering, verify `FRONTEND_BASE_URL` points to the public frontend |
| LinkedIn says OAuth is not configured | Set client ID/secret and exactly matching redirect URI in `backend/.env`; enable appropriate OIDC scopes in the provider app |
| Browser reports CORS errors | Set `BACKEND_CORS_ORIGINS` to the exact browser origin; prefer Nginx's same-origin `/api/` proxy |
| Cloudflare returns 1033 | Confirm the cloudflared container is connected, tunnel token matches the intended named tunnel, and published hostname routes target reachable frontend/API services |
| Local sign-in tokens fail | Generate and keep a stable `SECRET_KEY`; changing it invalidates previously issued tokens |

## Scope and limitations

Reports are general summaries for internal review and accreditation preparation; they are not official NAAC, AICTE, or NIRF templates. LMS/ERP synchronization and institution-specific report formats are not implemented. Faculty assignments are enforced by the API. Public portfolios include only verified activities and milestones; sharing can be revoked. AI recommendations are advisory and never make verification decisions.

No license is currently provided. Choose and add one only after the repository owners make that legal decision.
