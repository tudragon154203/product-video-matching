# Spec — Global Route Loading Screen (App Router)

## 1) Objective  
Show a **global loading screen** during route transitions to reduce perceived latency and avoid flicker.

## 2) Scope  
- Applies to **all** routes under `app/[locale]/**`.  
- Works for **client-side navigations** (Next.js `Link`, `router.push/replace`) and **programmatic redirects**.  
- Text is localized using existing message bundles (use `common.loading`).

## 3) UX Requirements  
- Full-screen overlay that **blocks interaction** until navigation settles.  
- Shows a neutral spinner/progress cue and localized label (EN/VI). Use the existing “Loading.” copy for now.  
- **No flicker**: if navigation resolves too fast (<150 ms), keep overlay hidden.  
- **Accessibility**: page container announces busy state (e.g., `aria-busy=true` on transition) and overlay has an SR-only label.  
- **Theming**: respects dark/light modes (follows app theming defaults).

## 4) Architecture & Integration Points  
- **State host**: Global provider stack you already render via `Providers` (TanStack Query root + Toaster). Hook loading state into this tree so it’s available app-wide.  
- **Where it wires**:  
  - `app/[locale]/layout.tsx` wraps pages; mount the loading overlay here so it persists across routes.  
  - `components/ui/providers.tsx` is the natural place to expose a loading context alongside QueryClient.  
- **Data-loading harmony**: The app already uses TanStack Query with smart caching/prefetch; the route loading UI is **only** for router-level transitions, not per-panel fetches. Keep panel-level skeletons as is.

## 5) Behavior Rules  
- **Enter** loading state when a route change is initiated.  
- **Exit** when the new route is committed (navigation success) or on error.  
- **Debounce** show (150 ms) to avoid flashing.  
- **Minimum visible time**: 300 ms to avoid blink on fast pages.  
- **Re-entrancy safe**: multiple rapid navigations don’t stack overlays.  
- **Error path**: if navigation errors, hide overlay and surface the page-level error UI (unchanged).

## 6) Content & Localization  
- Text key: `common.loading` (already exists in `messages/en.json` / `messages/vi.json`).  
- Future-proof: allow a follow-up key `common.loadingNewData` for cache-revalidation variants if needed.

---

## 7) Test-Driven Development (TDD) Plan

### 7.1 Test Strategy  
We will **write failing tests first**, then implement the smallest behavior to pass them, iterating until all acceptance tests pass. Layers:

1) **Unit tests (Jest + Testing Library)** for loading state transitions and a11y flags.  
2) **Integration tests (Jest)** to ensure the provider tree exposes/clears global loading.  
3) **E2E tests (Playwright)** to verify real navigation behavior, debounce, and minimum-visible timing within the actual Next runtime (re-use existing e2e harness).

### 7.2 Test Cases (write first)

#### A. Unit — State semantics
- **UC-01**: “Starts hidden” — on initial render, no loading state, no overlay.  
- **UC-02**: “Show on navigation start” — simulate route start; overlay becomes visible after **≥150 ms** debounce.  
- **UC-03**: “Hide on complete” — simulate navigation complete; overlay hides (respect **≥300 ms** minimum visible if it already showed).  
- **UC-04**: “Hide on error” — simulate route error; overlay hides.  
- **UC-05**: “Re-entrancy” — two quick navigations do not produce stacked overlays.  
- **UC-06**: “A11y busy flag” — container toggles `aria-busy` true/false properly and SR label exists.  
- **UC-07**: “Localization” — label pulls `common.loading` text from message bundle (EN/VI).

#### B. Integration — Provider & app shell
- **IT-01**: “Global provider wiring” — loading state is available under `Providers`; toggling state triggers overlay regardless of the page component tree.  
- **IT-02**: “Coexistence with TanStack Query” — panel-level fetching (prefetch/keepPreviousData) **does not** trigger the **route** overlay; only route transitions do.

#### C. E2E — Real navigation (Playwright)
- **E2E-01**: “Overlay appears on route change” — click link from `/[locale]/jobs` → `/[locale]/jobs/[jobId]`; assert overlay visibility.  
- **E2E-02**: “Debounce respected” — artificially fast route (mock) doesn’t show overlay (<150 ms).  
- **E2E-03**: “Minimum display” — overlay stays ≥300 ms once shown.  
- **E2E-04**: “Error path” — navigation error hides overlay and leaves page interactable.  
- **E2E-05**: “i18n label” — locale toggle shows localized label (use existing language toggle behavior for locale switch validation).

### 7.3 Test Data / Fixtures  
- **Navigation mocks** in Jest align with your existing `jest.setup.js` that stubs `next/navigation`, keeping tests deterministic.  
- For E2E timing, use Playwright’s timers and route interception to simulate “fast” vs “slow” navigations.

### 7.4 TDD Workflow  
1) Write **UC-01..UC-07** unit tests → run, ensure failures.  
2) Implement minimal state store + event listeners until all unit tests pass.  
3) Write **IT-01..IT-02** → green.  
4) Add **E2E-01..E2E-05**; adjust debounce/min-visible constants to meet UX criteria.  
5) Refactor (if needed) to keep implementation small and provider-centric; keep tests green.

---

## 8) Acceptance Criteria (Definition of Done)  
- ✅ All **unit/integration/E2E tests pass** and are required in CI.  
- ✅ Overlay appears only for **route** transitions; panel data prefetch is unaffected (continues using TanStack Query patterns documented in Sprint 3).  
- ✅ Label uses existing i18n keys for EN/VI.  
- ✅ A11y verified (busy state; SR label).  
- ✅ No visual flicker on ultra-fast navigations; no stacked overlays.  
- ✅ Works across locales under `app/[locale]/**` and within your current provider tree.

---

## 9) Risks & Mitigations  
- **Risk**: Overlay conflicts with panel-level loading UX.  
  - **Mitigation**: Scope overlay strictly to **router events**; panels keep skeletons (TanStack Query remains source of truth for data-fetch UX).  
- **Risk**: Flaky E2E due to timing.  
  - **Mitigation**: Use deterministic route interception (delay) and assert durations with generous thresholds.

---

## 10) Rollout Plan  
1) Merge behind a **feature flag** (`NEXT_PUBLIC_ENABLE_ROUTE_LOADING=1`).  
2) Ship to dev → verify with existing e2e suites.  
3) Enable on staging → 24h smoke.  
4) Enable in prod; keep flag for quick rollback.
