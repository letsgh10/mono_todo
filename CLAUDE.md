# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Monorepo for a Todo app with AI-assisted task prioritization. Each service has its own detailed
`CLAUDE.md` — read it before changing code there; this file covers only what spans services.

| Path | Stack | Details |
|---|---|---|
| `services/backend` | FastAPI, SQLModel/SQLite, Alembic, OpenAI | `services/backend/CLAUDE.md` |
| `services/frontend` | React 18 + Vite, single-file `App.jsx`, UI in Polish | `services/frontend/CLAUDE.md` |
| `services/e2e` | pytest + Playwright (sync API), page objects | `services/e2e/CLAUDE.md` |
| `services/mcp_tool` | FastMCP server generated from the backend's `/openapi.json` | — |

The services were imported as git subtrees (`git subtree pull --prefix=services/<name> ...`, see
`README.md`), so prefer keeping changes scoped to one service per commit.

## Commands

```bash
./install.sh   # venv + pip install -e ".[dev]", npm install, generates services/backend/.env, alembic upgrade head
./start.sh     # backend :8000 (uvicorn --reload) + frontend :5173 (vite); Ctrl+C stops both
```

Requires Python 3.11+ and Node 18+ (CI uses 3.11 and Node 20). Swagger UI: http://localhost:8000/docs.

Backend (from `services/backend`, venv active):

```bash
pytest                                             # all tests
pytest tests/test_tasks_api.py::test_create_task   # single test
ruff check app tests && black app tests            # lint + format (line length 100)
alembic revision --autogenerate -m "..."           # new migration
```

Frontend (from `services/frontend`): `npm run build`. There is no frontend test framework or linter —
UI behaviour is verified only by E2E.

E2E (from `services/e2e`, needs `./start.sh` running): `.venv/bin/pytest -n auto`, single test
`.venv/bin/pytest "test_tasks.py::TestAddTask::test_add_task_appears_on_list"`. The `e2e-runner`
agent (`.claude/agents/e2e-runner.md`) starts the stack and runs the suite, returning only a summary.

## CI (`.github/workflows/`)

- **backend.yml** — `ruff check`, `black --check`, `alembic upgrade head` on a fresh DB, pytest with
  `--cov-fail-under=80`, then `mutmut run`. Keep coverage above 80%.
- **frontend.yml** — `npm ci && npm run build` only.
- **e2e.yml** — runs on changes to any service; builds the frontend and serves it with `vite preview`,
  so the E2E suite must pass against a production build, not only the dev server.

## Cross-service architecture

- **Auth:** JWT from `/auth/*`, stored by the frontend in `localStorage` as `token` and sent as
  `Bearer`. The WebSocket can't send headers, so `/ws/projects` takes it as `?token=`; invalid token →
  close code 4401, which the frontend treats as logout.
- **Dev proxy:** Vite proxies `/auth`, `/tasks`, `/categories`, `/projects` and `/ws` to `localhost:8000`.
  A new top-level backend router prefix must also be added to `services/frontend/vite.config.js`.
- **Projects are WebSocket-only in the frontend.** The protocol lives in
  `services/backend/app/schemas/realtime.py` (commands carry a `request_id` echoed in
  `ack`/`members`/`error`) and is consumed by `connectProjects` in `api.js` and `useProjectsSocket` in
  `App.jsx`. Changing a message shape means changing both sides plus `services/e2e/pages.py`.
  REST task mutations push `task_created/updated/deleted` events to the owner and project members.
- **AI priority:** `OPENAI_API_KEY` in `services/backend/.env` switches from the deterministic
  `MockAIPriorityService` to OpenAI. E2E tests require the mock (due date within 3 days → `high`;
  keywords like `pilne`, `urgent`, `egzamin` change priority), and `start.sh` sources `.env`, so a key
  left there breaks the E2E suite.
- **UI text is Polish**, and E2E locators match it (`get_by_role("button", name="Wyloguj")`), so
  renaming a label in `App.jsx` requires updating `services/e2e/pages.py`.

## Notes

- Endpoint `async def` vs `def`: follow `services/backend/CLAUDE.md` (`async` only when awaiting the
  AI service). The `projekt` skill's "async def for all endpoints" line is outdated.
- `services/EPICS.md` holds the backlog of planned features (in Polish).
- `services/mcp_tool/.mcp.json` contains hardcoded paths from another machine; fix them before using it.
- Project settings deny reading `.env` and `*.db` files.
