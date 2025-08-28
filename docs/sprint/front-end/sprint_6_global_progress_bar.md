# Spec — Global Route Progress Bar (App Router)

## 1) Objective  
Show a **global progress bar** during route transitions to provide visual feedback for navigation and reduce perceived latency.

## 2) Scope  
- Applies to **all** routes under `app/[locale]/**`.  
- Works for **client-side navigations** (Next.js `Link`, `router.push/replace`) and **programmatic redirects**.  
- Uses industry-standard `nextjs-progressbar` library.

## 3) UX Requirements  
- **Thin progress bar** at the top of the page during navigation.  
- Shows **smooth animation** from start to finish of route transition.  
- **No flicker**: automatically handles fast navigations with smart timing.  
- **Clean design**: minimal distraction, unobtrusive but visible progress indication.  
- **Theming**: respects app color scheme (blue color by default).

## 4) Architecture & Integration Points  
- **Integration point**: Global provider stack via `Providers` (TanStack Query root + Toaster).  
- **Where it wires**:  
  - `components/ui/providers.tsx` is the natural place to include the progress bar alongside QueryClient.  
- **No custom state management**: Leverages built-in Next.js routing events from `nextjs-progressbar`.  
- **Data-loading harmony**: The app already uses TanStack Query for data loading; the progress bar is **only** for router-level transitions and doesn't interfere with data fetch UX.

## 5) Behavior Rules  
- **Auto-starts** when route navigation begins (no manual trigger needed).  
- **Auto-completes** when the new route is committed or on error.  
- **Smart timing**: Built-in delay handling prevents flicker on fast navigations.  
- **No overlap**: Multiple rapid navigations don't cause visual artifacts.  
- **Error handling**: Automatically handles navigation errors and resets progress.

## 6) Configuration  
- **Library**: `nextjs-progressbar` 
- **Color**: Blue (`#3B82F6`) to match app branding
- **Height**: 3px for subtle appearance
- **Animation**: Smooth transitions with 400ms stop delay

---

## 7) Test-Driven Development (TDD) Plan

### 7.1 Test Strategy  
We will verify the progress bar integration works correctly with minimal custom code. Since `nextjs-progressbar` is a battle-tested library, we focus on integration testing rather than unit testing its internals.

1) **Integration tests (Jest)** to ensure the progress bar is properly integrated into the provider tree.  
2) **E2E tests (Playwright)** to verify real navigation behavior and visual progress indication within the actual Next runtime (re-use existing e2e harness).

### 7.2 Test Cases (write first)

#### A. Integration — Provider & app shell
- **IT-01**: "Progress bar integration" — progress bar component renders correctly in provider tree without errors.  
- **IT-02**: "No conflicts with existing providers" — progress bar coexists with TanStack Query, Toaster, and other providers without interference.

#### B. E2E — Real navigation (Playwright)
- **E2E-01**: "Progress bar appears on route change" — click link from `/[locale]/jobs` → `/[locale]/jobs/[jobId]`; assert progress bar visibility.  
- **E2E-02**: "Smooth animation" — progress bar animates smoothly from start to finish during navigation.  
- **E2E-03**: "Fast navigation handling" — progress bar doesn't flicker on fast navigations.  
- **E2E-04**: "Error handling" — navigation error resets progress bar properly.  
- **E2E-05**: "Multi-step navigation" — progress bar handles multiple rapid navigations correctly.

### 7.3 Test Data / Fixtures  
- Navigation scenarios using existing app routes (`jobs`, job details, etc.)  
- Use Playwright's visual testing capabilities to verify progress bar appearance and animation.

### 7.4 TDD Workflow  
1) Write **IT-01..IT-02** integration tests → run, ensure they pass with the `nextjs-progressbar` implementation.  
2) Add **E2E-01..E2E-05**; verify progress bar behavior matches UX expectations.  
3) Ensure no visual regressions in existing test suites.

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
