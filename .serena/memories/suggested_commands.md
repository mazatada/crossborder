# Suggested commands for this repo
- `git status` / `git diff HEAD` / `git log -1` (Darwin shell defaults to zsh; the repo uses standard git CLI). Use `ls` to inspect directories and `pwd`/`cd` for navigation. Use `rg <pattern>` for fast search.
- `docker compose up --build` (or `docker-compose up --build`) from the repo root to start Postgres + backend + worker/scheduler services; services respect `.env` and `docker-compose.yml` definitions.
- `docker compose down` to tear down the Compose stack and `docker compose logs backend` when debugging.
- `cd backend && pip install -r requirements.txt` plus `cd backend && alembic upgrade head` to sync the DB schema (Alembic configs live under `backend/alembic` and `backend/migrations`).
- `cd backend && python -m flask run --host=0.0.0.0 --port=5000` when running the API locally without Compose; environment variables (SQLALCHEMY_DATABASE_URI, API_KEYS, WEBHOOK_URL, etc.) mirror `.env`.
- `python3 backend/app/jobs/cli.py --mode worker` / `--mode scheduler` (the Compose worker/scheduler override the entrypoint to run these loops).
- `cd frontend && npm install` followed by `cd frontend && npm run dev` to start the Vite dev server, which hits `import.meta.env.VITE_API_BASE` for `/v1` endpoints.
- Inspect docs/spec: `cat docs/spec/SPEC.md`, `cat docs/ui/frontend_mvp_ui_spec.md`, or run `rg <keyword> docs/implementation_plan_*` for requirements and roadmap.
