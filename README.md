# VeriSphere

VeriSphere is an academic progress and evidence-verification portal. Students follow curriculum milestones and submit evidence; faculty review that work; administrators provision faculty and monitor campus activity.

## Run with Docker

Docker Compose builds the API and frontend, persists the SQLite database in a named volume, and serves the application at <http://localhost:5176>. The API docs are at <http://localhost:8088/docs>.

```sh
docker compose up --build
```

The first run creates a starter B.Tech Computer Science course and its sample learning milestones. Students can sign up from the landing page. To provision the first administrator, set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` (at least 12 characters) in the shell or a local, uncommitted root `.env` file before starting Compose. The administrator can then create faculty accounts from the Accounts view. Configure `GROQ_API_KEY`, `GEMINI_API_KEY`, or both in the root `.env` to enable the learning assistant; Groq is tried first and Gemini is used as a fallback. Assistant chat and relevant progress context are sent to the configured provider. Faculty prompts use anonymized pending-submission summaries; students receive their own course and milestone context.

For production, set `APP_ENV=production`, provide a unique high-entropy `SECRET_KEY`, and configure a production database URL. The API accepts async SQLite and PostgreSQL URLs. Keep provider credentials and database secrets in the deployment environment or an untracked `.env` file; never commit them.

## Run locally

Start the API:

```sh
cd backend
if [ ! -f .env ]; then cp .env.example .env; fi
python3 -m pip install -r requirements-dev.txt
python3 main.py
```

Add provider keys to `backend/.env` to enable AI chat locally. The application loads this file without replacing variables already set in the environment. Copy it to the repository root instead when using Docker Compose, which reads root `.env` for container configuration.
`HOST`, `PORT`, `DEBUG`, and `WORKERS_COUNT` control the local server when started with `python3 main.py`. Debug mode enables reload and uses one worker; in production, set `DEBUG=false` to use the configured worker count. To use `uvicorn main:app` directly, pass the desired Uvicorn host, port, reload, and worker options on the command line.

This setup installs dependencies into the global Python environment. Install the project requirements rather than only `pwdlib`: VeriSphere uses Argon2 password hashing, provided by the `pwdlib[argon2]` extra. Installing `pwdlib` by itself does not install that hashing backend. Use `python3 -m pip` and `python3` so packages are installed for the interpreter that runs the app.

To run the backend tests, invoke pytest from `backend`:

```sh
python3 -m pytest
```

In another terminal, run the frontend:

```sh
cd frontend
npm ci
npm run dev
```

The Vite development server proxies `/api` and `/health` to the API on port 8088. The API uses `sqlite+aiosqlite:///./verisphere.db` by default and creates the initial schema and sample curriculum on startup. Set `DATABASE_URL` to use another supported database. Alembic migrations are available under `backend/alembic`.

## Main flows

- Student registration, sign-in, curriculum milestone tracking, evidence submission, and progress overview.
- Role-protected faculty review with verification or revision feedback; verification unlocks the next milestone.
- Student learning guidance and faculty feedback suggestions through the AI assistant, using configured Groq and/or Gemini providers.
- Administrator overview and account directory, plus faculty account provisioning.
- Public course and announcement endpoints.

Authentication endpoints issue signed bearer tokens. Public registration is restricted to student accounts; teacher accounts are provisioned by an administrator and the initial administrator is configured through environment variables.