# Sprint 11 - Front-End: Matching Phase Panel (PRD)

## Document Status
- **Type**: Product Requirements Document (PRD)
- **Sprint**: 11
- **Last Updated**: 2025-11-21
- **Status**: Proposed

## 1. Background and Problem
- The Job Detail page surfaces collection and feature extraction context but shows almost nothing when a job enters `matching` beyond the phase label/percent. Operators cannot tell whether the matcher is progressing, stalled, or producing any matches until evidence generation finishes.
- The existing results list (`/results?job_id=...`) is not surfaced in the Job Detail view, so users cannot preview matches as they are produced.
- There is no visibility into matching health signals (candidate throughput, queue depth, last event time) that would help triage incidents before the job times out or fails.

## 2. Goals
1) Provide a dedicated Matching Phase panel on the Job Detail page with real-time progress, health signals, and early match previews.
2) Let operators confirm that `match.result` events are flowing (or detect stalls) within one poll cycle after the phase starts.
3) Keep the panel useful after the phase ends by collapsing into a summary that shows what was matched (or that nothing matched).
4) Reuse existing data contracts wherever possible; add one focused summary endpoint to avoid heavy client-side aggregation.

## 3. Non-Goals
- Changing the matching algorithm or scoring logic.
- Implementing WebSocket streaming (polling is acceptable for this sprint).
- Building a full evidence gallery (only small evidence previews in the panel).
- Bulk operations on matches (delete/flag); those belong to a later sprint.

## 4. Users and Use Cases
- **Operators/SRE**: Check whether the matcher is alive, whether queues drain, and whether `matchings.process.completed` is approaching.
- **Analysts/QA**: Preview top matches while the job is still in `matching` to validate quality before evidence is ready.
- **Product/CS**: Confirm that jobs are producing value (matches found) and identify empty-result runs quickly.

## 5. Scope
- **In scope**
  - New `MatchingPanel` rendered on `app/[locale]/jobs/[jobId]/page.tsx` when `phase === 'matching'` (stay mounted as a collapsed summary for `evidence` and `completed`).
  - Data plumbing via React Query: new `useMatchingSummary(jobId)` plus existing `useJobMatches(jobId, ...)`.
  - UI pieces: stage banner, progress + health cards, live matches list with filters, empty/error states.
  - Minimal evidence preview slot (thumbnail or placeholder) if `evidence_path` is present on a match.
- **Out of scope**
  - New navigation routes for match detail (can open a drawer/modal only).
  - Any changes to `matcher` worker behavior or event schemas.
  - Cross-job aggregated dashboards.

## 6. Data Contracts and API Requirements

### 6.1 Matching Summary Endpoint (new)
- **GET `/jobs/{job_id}/matching/summary`**
- Purpose: lightweight aggregation for the active matching run to avoid calculating totals on the client.
- **Response (proposed)**:
```json
{
  "job_id": "uuid",
  "status": "pending | running | completed | failed",
  "started_at": "2025-11-21T10:00:00Z",
  "completed_at": null,
  "last_event_at": "2025-11-21T10:05:12Z",
  "candidates_total": 180,
  "candidates_processed": 75,
  "vector_pass_total": 180,
  "vector_pass_done": 75,
  "ransac_checked": 40,
  "matches_found": 18,
  "matches_with_evidence": 6,
  "avg_score": 0.64,
  "p90_score": 0.82,
  "queue_depth": 12,
  "eta_seconds": 210,
  "blockers": []
}
```
- Accept `force_refresh=true` query param for manual retries from the UI. Return 404 if job is missing; return `status: completed` and cached stats if the phase has advanced.

### 6.2 Matches Feed (existing)
- **GET `/results?job_id={job_id}&limit={n}&offset={m}&min_score={x}`** (already wrapped by `useJobMatches`).
- Match shape: `MatchResponse` (`match_id`, `score`, `best_img_id`, `best_frame_id`, `evidence_path`, enriched titles).
- **GET `/matches/{match_id}`** for detail drawer (already implemented in API client).
- Evidence: `evidence_path` (if present) can be turned into `<img src={`/api/proxy?path=${evidence_path}`}>` as today.

### 6.3 Event Hooks (observability only)
- Phase starts at `match.request`; completion signaled by `matchings.process.completed`.
- Each `match.result` corresponds to one `MatchResponse` row; use `last_event_at` + `matches_found` deltas to infer liveness.

## 7. UX and Interaction Overview
- Panel appears directly under `JobStatusHeader` and above the collapsed `FeatureExtractionPanel` when `phase === 'matching'`.
- States:
  - **Running**: live progress bars for vector search and geometric verification, health chips (queue depth, last event age), and a streaming matches list.
  - **Completed/Evidence**: panel collapses to a summary bar (matches found, best score, time to complete) with the list still accessible on expand.
  - **Failed**: error banner with retry for summary refresh and a link to logs (copy-to-clipboard job_id).
- User controls:
  - Score filter slider (`min_score`) with debounced refetch.
  - Sort by `score DESC` (default) or `created_at DESC`.
  - Toggle to show only matches that already have evidence.
  - Manual `Refresh` button (calls summary + matches in parallel).

## 8. Layout and Component Specifications

### 8.1 Placement and Structure
- Insert `<MatchingPanel>` in `app/[locale]/jobs/[jobId]/page.tsx` after `JobStatusHeader` and before `FeatureExtractionPanel` (which is already collapsible in matching/evidence).
- Export from `components/jobs/MatchingPanel/index.ts` with subcomponents for readability.

### 8.2 Summary Banner
- Left: title + description from `t('matching.panel.title')` / `t('matching.panel.body')`.
- Right: percent pill (derived from summary `candidates_processed / candidates_total` or fallback to job `percent`), optional ETA chip.
- Background: subtle purple gradient to differentiate from collection (blue) and feature extraction (yellow).

### 8.3 Progress and Health Cards
- Cards (3-up on desktop, stacked on mobile):
  1) **Pairs processed**: determinate bar using `candidates_processed` / `candidates_total`; show raw counts.
  2) **Matches found**: number + mini chart sparkline from last 5 polls (stored in component state).
  3) **Evidence ready**: `matches_with_evidence` / `matches_found`; show badge if evidence is still pending.
- Health row under cards:
  - Queue depth chip (warning if > 50).
  - Last event age chip (warning if > 60s).
  - Status pill (`running`, `blocked`, `completed`, `failed`).

### 8.4 Live Matches List
- Data source: `useJobMatches(jobId, { limit: 25, offset: 0, min_score })`.
- Columns: Product title, Video title + timestamp, Score (with bar), Evidence badge (Ready / Pending), Created at.
- Each row opens a right-side drawer using `getMatch()` to show the enriched product/video cards and evidence preview (if available).
- Empty state:
  - During running: skeleton rows + message “Waiting for matches…”
  - After completion with zero matches: “No matches found for this job” with hint to adjust score threshold.

### 8.5 Collapsed Summary (post-matching)
- When phase transitions to `evidence` or `completed`, collapse the panel automatically to a 1-row summary:
  - Matches found, best score, duration of matching, evidence coverage (`matches_with_evidence / matches_found`).
  - Expand chevron keeps previously loaded list and summary data; no additional polling unless user hits Refresh.

## 9. Data and State Management
- New hook: `useMatchingSummary(jobId, enabled, refetchInterval)` using React Query (`queryKeys.matching.summary`).
  - `enabled`: true when phase is `matching` or `evidence`.
  - `refetchInterval`: 4000ms during `matching`, `false` otherwise.
  - Cache time: 0 (always fresh during active phase).
- Matches polling:
  - `useJobMatches(jobId, params, enabled)` with `enabled` for `matching|evidence|completed`.
  - `refetchInterval`: 5000ms during `matching`, disabled afterward unless user clicks Refresh.
- Derived fields:
  - `progressPercent = candidates_total ? Math.round((candidates_processed / candidates_total) * 100) : percent || 80`.
  - `isStalled` flag if `now - last_event_at > 60s` while status is `running`.
- Graceful fallback: if summary endpoint returns 404 or missing totals, show indeterminate bars but keep matches list visible.

## 10. Accessibility and i18n
- All controls and pills receive `aria-label`; progress bars expose `aria-valuenow/min/max`.
- Live region (`aria-live="polite"`) for the summary banner updates.
- Respect `prefers-reduced-motion` for progress bar animations.
- Add translation keys under `messages/en/matching.json` (and mirrored locales if present).

## 11. Telemetry and Observability
- Emit analytics events:
  - `matching_panel_viewed` with `{ job_id, phase }`.
  - `matching_filter_changed` with `{ min_score, evidence_only }`.
  - `matching_manual_refresh` with `{ job_id }`.
- Log console warning + Sentry breadcrumb if `isStalled` persists for >2 polls or if summary repeatedly fails.

## 12. Implementation Plan (no code)
1) **API layer**: Add `matching.summary` endpoint to `MAIN_API_ENDPOINTS`, implement `MatchingSummaryResponse` Zod schema, and create `useMatchingSummary` hook with query key namespace.
2) **Component**: Build `MatchingPanel` + subcomponents (`MatchingSummaryCards`, `MatchingHealthRow`, `MatchingResultsTable`, `MatchingDrawer`).
3) **Page wiring**: Insert panel in `app/[locale]/jobs/[jobId]/page.tsx`, pass `phase`, `percent`, `featureSummary` as today, and ensure the panel collapses after phase advance.
4) **i18n + styling**: Add copy to `messages/en`, reuse Tailwind palette (purple for matching), and add skeleton placeholders.
5) **Tests**: Unit test hook polling behavior; component tests for states (running, empty, stalled, completed); Playwright path for end-to-end flow (start job -> matching -> panel shows matches -> evidence badge).

## 13. Acceptance Criteria
- Panel appears only when `phase === 'matching'` and remains accessible (collapsed) for `evidence`/`completed`.
- Progress cards show determinate bars when totals exist; fall back to indeterminate when totals are missing without breaking UI.
- Live list populates with `match.result` data within one poll when matches exist; shows empty-state messaging otherwise.
- Stalled detection (>60s since last event) surfaces a warning chip without blocking the UI.
- Evidence badge reflects `evidence_path` presence; toggling “evidence only” filters the list accordingly.
- Manual Refresh triggers both summary and list refetch and updates the UI.

## 14. Testing Plan
- **Unit**: `useMatchingSummary` polling intervals, derived progress percent, stalled flag; `MatchingPanel` rendering for each state.
- **Integration**: Render Job Detail with mocked React Query data to verify placement, collapse behavior after phase change, filter interactions.
- **E2E (Playwright)**:
  - Start a job, mock API to emit matches during `matching`; assert progress cards update and rows appear.
  - Complete matching with zero matches; assert empty-completed message.
  - Simulate stalled summary (no `last_event_at` change); assert warning chip appears.

## 15. Risks and Mitigations
- **Backend summary not ready**: Keep UI usable by falling back to `%` from `JobStatus` and matches feed alone; guard against missing totals.
- **Large result sets**: Default to limit 25 with pagination controls; lazy-load on demand to avoid heavy DOM.
- **Polling load**: Share polling interval across summary and matches; stop polling immediately on `completed`/`failed`/`cancelled`.
- **Evidence lag**: Evidence badges should tolerate nulls; copy clarifies that evidence may trail matching completion.

## 16. Success Metrics
- Mean time to detect matching stalls (should drop vs. baseline with no panel).
- Panel load error rate (<1% of requests).
- Time from phase start to first visible match (<1 poll cycle when matches exist).
- User engagement: percentage of job-detail sessions where the matching panel is expanded during `matching`.

## 17. Open Questions
- Do we have a reliable backend estimate for `candidates_total`? If not, should the UI display “estimated” and expose tooltip with calculation?
- Should the list auto-scroll to top on new data during running, or keep user scroll position?
- Do we need a feature flag to gate rollout, or can we ship directly once backend summary is available?
