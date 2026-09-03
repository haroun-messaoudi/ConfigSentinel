# ConfigSentinel — Frontend

Vue 3 + TypeScript + Vite + Pinia + Vue Router + Tailwind CSS v4.

## Getting started

```bash
npm install
cp .env.example .env   # point VITE_API_BASE_URL at your Django backend
npm run dev
```

## Architecture: feature-based, not type-based

Instead of grouping files by *kind* (`components/`, `views/`, `stores/` all
mixed together for the whole app), each business domain of ConfigSentinel
owns its own folder under `src/features/`, with its own components,
composables, store and types inside it. This keeps everything related to
"devices" in one place instead of scattered across four global folders —
it's the structure that scales as the app grows past a handful of screens.

```
src/
├── api/            # Axios instance, JWT injection, refresh-on-401, error normalization
├── assets/styles/  # Tailwind entry point + design tokens
├── components/     # Truly generic, feature-agnostic UI (buttons, modals, tables)
│   ├── common/
│   └── layout/
├── composables/     # Generic reusable composables (not tied to one feature)
├── features/
│   ├── auth/         # login, JWT session, role checks
│   ├── devices/       # device inventory (list/detail/pause/resume)
│   ├── changes/       # ConfigChange review, acknowledge, set_baseline
│   ├── alerts/        # alert feed
│   └── detection/     # SeverityClass / TrackedConcept / DetectionProfile (admin)
│       └── <feature>/
│           ├── api.ts          # calls into this feature's DRF endpoints
│           ├── components/     # *View.vue components routed to, + subcomponents
│           ├── composables/    # feature-specific composables (e.g. useDeviceFilters)
│           ├── stores/         # Pinia store(s) for this feature
│           └── types/          # TS interfaces matching the DRF serializers
├── layouts/         # DefaultLayout (sidebar nav) — App.vue itself stays chrome-free
├── router/          # routes + auth/role navigation guards
├── stores/          # cross-cutting Pinia stores only (none yet beyond auth)
├── types/           # types shared across features (User, PaginatedResponse, ApiError)
├── utils/           # pure helper functions
└── views/           # top-level pages with no natural feature home (Dashboard, 404)
```

**Rule of thumb:** if a component/store/type is only ever used by one
feature, it lives inside that feature's folder. It only graduates to
`src/components`, `src/stores`, or `src/types` once a second feature needs
it too.

## Auth & roles

- JWT access token lives in memory only (`api/client.ts`); the refresh
  token is the only thing persisted (`localStorage`), and is exchanged for
  a fresh access token on app boot (`authStore.restoreSession`) and
  transparently on any 401 (`registerRefreshHandlers`).
- Roles mirror the backend exactly: `admin`, `operator`, `viewer`
  (see `src/types/index.ts`).
- Route-level access is declared per-route via `meta: { requiresAuth, roles }`
  in `src/router/index.ts` and enforced in the global `beforeEach` guard.
  Component-level conditionals (e.g. hiding a nav link) use
  `authStore.hasRole('admin')`.

## Conventions

- Path alias `@/` → `src/` (configured in `vite.config.ts` and
  `tsconfig.app.json`).
- Every feature's `api.ts` is the *only* place that calls `apiClient`
  directly for that feature — components call the store or a composable,
  never the API layer directly.
- Tailwind v4: no `tailwind.config.js` — the `@theme` block in
  `src/assets/styles/main.css` is where design tokens (colors, etc.) live.

## Next step

Build out the placeholder components (`DeviceListView`, `ChangeListView`,
`AlertListView`, `DetectionProfileListView`, `LoginView`, `DashboardView`)
against the real DRF endpoints, starting with auth so every other screen
can assume a logged-in user.
