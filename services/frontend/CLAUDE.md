# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev       # Start dev server at http://localhost:5173
npm run build     # Production build
npm run preview   # Preview production build
```

No test framework is configured.

## Architecture

This is a React 18 + Vite SPA for a todo/task management app with AI-assisted priority analysis. The UI is in Polish.

**Backend:** The Vite dev server proxies `/auth`, `/tasks`, `/categories` and `/projects` to `http://localhost:8000`, and `/ws` (WebSocket) to `ws://localhost:8000`.

### Source layout

```
src/
├── main.jsx          # React 18 entry point
├── App.jsx           # All components (single-file architecture)
├── api.js            # Centralized API client
└── styles/index.css  # All styles with CSS variables
```

### Component structure (all in App.jsx)

- **ToastProvider / useToast** — context-based toast notifications, auto-dismiss at 3.5s
- **AuthPage** — login/register tabs
- **TaskModal** — create/edit form; includes AI priority analysis via `reanalyzePriority()`
- **CategoryModal** — create category with color picker
- **ProjectModal / MembersModal** — create a project; list, add and remove members (driven by the projects socket)
- **HistoryModal** — change history of a task (`GET /tasks/{id}/history`, oldest first, shown newest first); loading / empty / error-with-retry states; opened from the clock button on `TaskCard`
- **useProjectsSocket** — hook owning the live project list, cached member lists and the socket status (`connecting` / `online` / `offline`); fires `onMembershipChanged` so the Dashboard reloads tasks, and `onUnauthorized` (close code 4401) which logs the user out
- **TaskCard** — task row with priority badges, tags, due date status, AI indicator
- **Sidebar** — graphite side panel: saved views (Wszystkie / Do zrobienia / Ukończone / Pilne / Przeterminowane) that map onto the task filters, projects and categories sections, user profile with logout; off-canvas below 1024px
- **EmptyState** — illustrated "Brak zadań" placeholder inside the task board
- **Dashboard** — main view; topbar (page title + live socket status chip), hero panel with counters, filter panel (view tabs + status/priority selects), tag search + "Nowe zadanie", task board grouped into "Do zrobienia" / "Ukończone"
- **App** — root component; manages auth state via localStorage, renders AuthPage or Dashboard

### API client (api.js)

Token stored in `localStorage` as `token`, sent as `Bearer` header. Functions:
- Auth: `register`, `login`, `logout`
- Tasks: `getTasks`, `createTask`, `updateTask`, `deleteTask`, `addTag`, `removeTag`, `reanalyzePriority`, `getTaskHistory`, `getUpcomingTasks`
- Categories: `createCategory`, `deleteCategory`
- Projects: `connectProjects({ onMessage, onStatus })` — opens `/ws/projects?token=…`, reconnects with exponential backoff (max 30 s), returns `{ send(command) → Promise, close() }`. `send` attaches a `request_id` and resolves on the matching `ack`/`members` reply or rejects on `error` (codes mapped to Polish labels in `WS_ERROR_LABEL`). Projects have no REST calls in the frontend.

### Styling

Light theme ported from the Figma Make design, all in `index.css` with CSS variables. No CSS framework or preprocessor. Palette: paper background `#f2f0e9` with a faint grid, graphite sidebar `#14171f`, cobalt hero `#3c46e8`, lime accent `#c8ff3d`, coral `#ff715b` for errors. Font: Manrope (Google Fonts link in `index.html`). Icons are inline stroke SVGs (`Icon` component in `App.jsx`), no icon font or emoji. Breakpoints: sidebar becomes off-canvas ≤1023px, hero collapses ≤900px, single-column toolbar ≤639px.
