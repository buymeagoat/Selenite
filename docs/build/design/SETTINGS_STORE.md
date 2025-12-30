# SETTINGS-STORE Design

Task: `[SETTINGS-STORE] Shared settings provider & cache`

## Objectives
1. Provide a single source of truth for admin/user settings that any React surface (dashboard, modals, transcript page, future admin SPA) can consume without re-implementing fetch logic.
2. Hydrate UI immediately using cached values while validating freshness in the background.
3. Standardize error handling, retries, and manual refresh prompts so UX remains consistent.
4. Offer test doubles/fakes so components can be exercised without touching the real API.

## Non-goals
- Splitting settings schemas into user/admin tables (tracked separately).
- Changing backend `/settings` semantics (we will consume what exists today).
- Offline edit/merge conflict resolution.

## High-level Design

### Data Model
- `AdminSettings` (current API schema) + metadata: `version`, `fetchedAt`, `source` (cache/network), `status` (`idle | loading | ready | error`).
- Cache stored in `localStorage` under `selenite_admin_settings_v1`. Future migrations bump suffix and transform/clear stale entries.

### Store/Provider
- `SettingsProvider` (React context) wraps the app (inside `AppRouter` soon).
- Maintains internal state `{data, status, error}` via reducer to keep transitions predictable.
- Hydrates synchronously from cache on mount (`status=ready` if data exists) and immediately kicks off a network refresh with abort/timeout (7s default, configurable).
- Exposes hook `useAdminSettings()` returning `{settings, status, refresh, error}`.
- Emits `window.dispatchEvent(new CustomEvent('selenite:settings-updated', ...))` only from provider so legacy listeners keep working until migrated.

### Fetch & Retry Strategy
- Single in-flight request tracked via `AbortController`; new refresh cancels previous.
- Timeout fallback (7s) triggers retry with exponential backoff (e.g., 2s, 4s, 8s up to max). Backoff pauses if browser offline (listen to `online/offline` events).
- On repeated failure, surface toast (once per session) and keep latest cached data; status becomes `error` but `settings` remains last known good.

### Events & Consumers
- Existing components replace bespoke `fetchSettings()` calls with `const {settings, status, refresh} = useAdminSettings()`.
- `NewJobModal` uses `status==='loading' && !settings` to show the loading message; when `settings` exists, controls stay enabled even if status flips back to `loading` due to refresh.
- Settings page uses `refresh()` on save success rather than managing its own event bus.

### Testing Strategy
- Export store internals via dependency injection (custom `fetcher` + `storage` adapters) to unit test timeouts, cache hydration, and event dispatch.
- Provide `MockSettingsProvider` utility for component tests (vitest) to inject deterministic settings/status.
- Update Playwright fixtures to seed cache (optional) so UI tests start with known defaults.

### Rollout Plan
1. Land provider + hook + tests (no consumers yet). Ensure provider is optional so we can wrap gradually.
2. Update `App.tsx` (or router entry) to wrap everything in `SettingsProvider`.
3. Migrate Dashboard/NewJobModal to hook (remove local fetch logic).
4. Migrate Settings page to hook so it displays live status and uses `refresh()` after saves.
5. Remove residual `selenite:settings-updated` listeners once all consumers rely on context.
6. Document usage in README/TESTING_PROTOCOL; update task log and run manual verification.

### Open Questions / Follow-ups
- Need to decide whether end-user (non-admin) settings will live in same provider or separate slice (likely same context with role-based selectors).
- Consider batching `fetchSettings` with other bootstrap data (jobs/tags) to reduce round trips-out of scope for this task but note for `[SETTINGS-STORE]` follow-ups.
