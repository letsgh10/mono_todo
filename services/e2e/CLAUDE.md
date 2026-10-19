# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# One-time setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

# Run all tests (headless)
.venv/bin/pytest

# Run in parallel (one test user per worker)
.venv/bin/pytest -n auto

# Run a single file / single test
.venv/bin/pytest test_auth.py
.venv/bin/pytest "test_tasks.py::TestAddTask::test_add_task_appears_on_list"

# Watch the browser / slow down / open the Playwright inspector
.venv/bin/pytest --headed
.venv/bin/pytest --headed --slowmo 500
PWDEBUG=1 .venv/bin/pytest test_tasks.py -k add_task

# Inspect a trace captured on failure
.venv/bin/playwright show-trace test-results/<test-name>/trace.zip
```

Environment variables: `BASE_URL` (frontend, default `http://localhost:5173`), `AUTH_URL` (backend, default `http://localhost:8000`). `--base-url` overrides `BASE_URL`.

## Prerequisites

Frontend and backend must be running (`./start.sh` from the repo root). The backend must run **without** `OPENAI_API_KEY`, so that `MockAIPriorityService` gives deterministic AI results (due date within 3 days → `high`).

Every pytest session (every xdist worker) registers its own user `e2e_<hex>@example.com` through the API. No pre-existing account is needed.

## Architecture

Playwright (sync API) + `pytest-playwright`. Chromium only, configured in `pytest.ini` together with screenshot and trace capture on failure (written to `test-results/`, gitignored).

**`conftest.py`** — fixtures:
- `api` / `user_api` — Playwright `APIRequestContext` to the backend, anonymous and authenticated as the session user. Used for registration, login, and cleanup, never for assertions that belong to the UI.
- `test_user`, `auth_token` — session-scoped; one registered user per session.
- `clean_tasks` — autouse; deletes all tasks of the session user through the API before and after every test. Tests do not clean up through the UI.
- `logged_in_page` — fresh browser context with the JWT injected via `storage_state`, already on the dashboard. Use the plugin's plain `page` fixture for logged-out scenarios.
- `browser_context_args` override — 1280×900 viewport, `pl-PL` locale (task cards format dates with `toLocaleDateString('pl-PL')`).

**`pages.py`** — page objects: `AuthPage`, `DashboardPage`, `TaskModal`, `ProjectsPanel`, `ProjectModal`, `MembersModal`. All selectors live here. Prefer role/placeholder/title locators (`get_by_role("button", name="Wyloguj")`, `get_by_placeholder("Co chcesz zrobić?")`, `get_by_title("Usuń")`); CSS classes only where the UI gives nothing better (`.task-card`, `.toast`, `.due-date`).

**Test files:**
- `test_auth.py` — registration, login, logout, session persistence
- `test_tasks.py` — add / edit / delete / toggle status
- `test_deadlines.py` — due dates, overdue filter, upcoming (7-day) view, AI priority with due date
- `test_projects.py` — create project, members (add / unknown email / remove), project chip filter, realtime push to a second user's dashboard (`other_user_page` fixture logs the second user in via the API; `ProjectsPanel.live_status` exposes the socket state)
- `test_views.py` — regression: sidebar counters ("Wszystkie", "Pilne", ...) stay stable when switching views

## Key patterns

- Web-first assertions only: `expect(locator).to_be_visible()`, `.to_have_count(0)`, `.to_have_class(re)`. No `time.sleep`, no manual polling. For "it must not appear" use `to_have_count(0)` (it waits for the element to go away) or check HTML5 validity via `AuthPage.form_is_valid()`.
- Task titles are unique per test (`unique_title()`), and `DashboardPage.task_card(title)` matches the title exactly. Avoid words the mock AI treats as keywords in titles (`deadline`, `pilne`, `urgent`, `important`, `low`, `later`, `egzamin`…), otherwise the priority changes.
- Native `confirm()` dialogs are handled with `page.once("dialog", ...)` inside `DashboardPage.delete_task(confirm=...)`. Playwright dismisses unhandled dialogs, which would silently cancel a delete.
- `input[type=date]` is uncontrolled in React (read via ref on submit), so `locator.fill("YYYY-MM-DD")` works directly.
- View filters (`show_overdue`, `show_upcoming`, `show_all`) wait for the matching `/tasks` response before asserting, so a "card still visible" assertion cannot pass on the stale list.
- Known backend gap, kept as `xfail(strict=True)`: `POST /tasks/priority/analyze` ignores `due_date`, so the "Sugestia AI" button does not raise priority for near deadlines (creation with "Użyj AI przy zapisie" does). Remove the marker once the backend passes `due_date` through.
