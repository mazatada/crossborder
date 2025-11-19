# Task completion checklist
- Always `git status` before/after coding to confirm no unrelated files are dirty, and use `git diff` to review what will be committed.
- Smoke-test the backend via Compose: `docker compose up --build` and then `curl http://localhost:5001/v1/health` (or another API) to ensure the Flask server responds; `docker compose down` afterward.
- When touching database models/migrations, run `cd backend && alembic revision --autogenerate -m "<summary>"` and `cd backend && alembic upgrade head` to keep migrations in sync with `.env`-driven Postgres.
- For frontend changes, `cd frontend && npm run dev` to verify the MVP tabs load (especially HS/Pack/PN interactions) since there is no automated UI test suite yet.
- Although there is no formal `pytest` suite yet, the docs plan for pytest+coverage (`docs/implementation_plan_7_devex_quality.md`), so run targeted pytest commands once tests land. In the meantime, ensure manual flows work if API surface changed.
