# Sprint 11 - Front-End: Matching Phase Panel

## Document Status
- **Type**: Frontend Implementation Document
- **Sprint**: 11
- **Last Updated**: 2025-11-21
- **Status**: Implemented

## 1. Overview
The Matching Phase Panel provides real-time visibility into the matching process on the Job Detail page. It displays progress, health signals, and live match results as they are produced by the matcher service.

## 2. Component Architecture

### 2.1 Main Components
- **MatchingPanel** (`components/jobs/MatchingPanel/MatchingPanel.tsx`)
  - Container component managing panel state and layout
  - Handles expanded/collapsed states with session storage persistence
  - Renders different views based on phase (active vs completed)
  
- **MatchingSummaryCards** (`components/jobs/MatchingPanel/MatchingSummaryCards.tsx`)
  - Three-card layout showing:
    1. Pairs Processed (progress bar with counts)
    2. Matches Found (count with avg/p90 scores)
    3. Evidence Ready (progress bar for evidence coverage)

- **MatchingHealthRow** (`components/jobs/MatchingPanel/MatchingHealthRow.tsx`)
  - Health indicators: queue depth, last event age, status pill
  - Warning states for stalled processing

- **MatchingResultsTable** (`components/jobs/MatchingPanel/MatchingResultsTable.tsx`)
  - Live matches list grouped by product
  - Score filter slider (min_score)
  - Evidence badges (Ready/Pending)
  - Polls every 5 seconds during active matching

- **MatchingBanner** (`components/jobs/MatchingPanel/MatchingBanner.tsx`)
  - Phase banner shown at top of page during matching
  - Displays percent and match count

### 2.2 Component Hierarchy
```
JobDetailsPage
├── MatchingBanner (phase === 'matching')
└── MatchingPanel (phase === 'matching' | 'evidence' | 'completed')
    ├── MatchingSummaryCards
    ├── MatchingHealthRow
    └── MatchingResultsTable
```

## 3. Data Management

### 3.1 React Query Hooks
**useMatchingSummary** (`lib/api/hooks.ts`)
```typescript
useMatchingSummary(
  jobId: string,
  enabled: boolean,
  refetchInterval: number | false
)
```
- Query key: `['matching', 'summary', jobId]`
- Polling: 4000ms during `matching` phase, disabled otherwise
- Stale time: 0 (always fresh)
- Endpoint: `GET /jobs/{job_id}/matching/summary`

**useJobMatches** (`lib/api/hooks.ts`)
```typescript
useJobMatches(
  jobId: string,
  params: { limit, offset, min_score },
  enabled: boolean,
  refetchInterval: number | false
)
```
- Query key: `['results', 'matches', jobId, params]`
- Polling: 5000ms during active matching
- Endpoint: `GET /results?job_id={job_id}&limit={n}&offset={m}&min_score={x}`

### 3.2 Data Flow
1. Page determines phase from `useJobStatusPolling`
2. `useMatchingSummary` enabled when phase is `matching`, `evidence`, or `completed`
3. Polling active only during `matching` phase
4. `MatchingPanel` receives summary data and passes to child components
5. `MatchingResultsTable` independently fetches matches with filters

## 4. State Management

### 4.1 Panel State
- **isExpanded**: Controlled via session storage (`matchingPanelExpanded`)
- Auto-collapses when phase advances from `matching` to `evidence`
- User can manually expand/collapse after phase completion

### 4.2 Filter State
- **minScore**: Local state in `MatchingResultsTable` (default: 0.8)
- Debounced via React Query's automatic refetch on param change
- Slider range: 0.0 to 1.0, step 0.05

## 5. UI States

### 5.1 Active Matching (phase === 'matching')
- Full panel expanded by default
- Live progress cards with determinate bars
- Health row with real-time indicators
- Streaming matches table with 5s polling
- Purple gradient background for phase differentiation

### 5.2 Completed/Evidence (phase !== 'matching')
- Collapsed summary bar showing:
  - Total matches found
  - Average score
  - Duration (started_at to completed_at)
  - Evidence coverage
- Expandable to show full details
- No active polling

### 5.3 Loading State
- Skeleton placeholders for cards (3 animated boxes)
- Skeleton rows for matches table

### 5.4 Error State
- Alert banner with retry button
- Separate error handling for summary vs matches
- Graceful degradation if summary unavailable

### 5.5 Empty State
- During matching: "Waiting for matches..." with skeleton
- After completion: "No matches found" with hint about score threshold

## 6. Page Integration

### 6.1 Placement (`app/[locale]/jobs/[jobId]/page.tsx`)
```typescript
// Order of components:
1. MatchingBanner (if phase === 'matching')
2. JobStatusHeader
3. MatchingPanel (if phase in ['matching', 'evidence', 'completed'])
4. FeatureExtractionPanel (if phase in ['feature_extraction', 'matching', 'evidence'])
5. CollectionSummary (accordion for products/videos)
```

### 6.2 Phase Detection
```typescript
const isMatchingPhase = phase === 'matching' || phase === 'evidence' || phase === 'completed';
const isActive = phase === 'matching';
```

### 6.3 Polling Control
- Summary polling: 4000ms during `matching`, disabled otherwise
- Matches polling: 5000ms during `matching`, disabled otherwise
- Both stop immediately when phase advances

## 7. Styling and Accessibility

### 7.1 Visual Design
- Purple gradient for matching phase (differentiates from collection blue, feature extraction yellow)
- Progress bars with determinate values when totals available
- Badge colors:
  - Green: Evidence ready
  - Amber: Evidence pending
  - Emerald: Phase complete

### 7.2 Accessibility
- `aria-expanded` on collapse/expand button
- `aria-controls` linking button to content
- `aria-label` on all interactive controls
- Progress bars expose `aria-valuenow/min/max`
- Respects `prefers-reduced-motion`

### 7.3 Responsive Design
- Cards: 3-up on desktop, stacked on mobile
- Table: Horizontal scroll on mobile
- Compact layout for collapsed summary

## 8. Internationalization

### 8.1 Translation Keys (`messages/en/matching.json`)
```json
{
  "jobMatching": {
    "complete.title": "Matching Complete",
    "cards.pairsProcessed": "Pairs Processed",
    "cards.matchesFound": "Matches Found",
    "cards.evidenceReady": "Evidence Ready",
    "cards.complete": "complete",
    "cards.avgScore": "Avg Score",
    "cards.p90Score": "P90 Score",
    "cards.evidencePending": "Evidence pending",
    "results.title": "Match Results",
    "results.minScore": "Min Score",
    "results.ready": "Ready",
    "results.pending": "Pending",
    "results.showing": "Showing {count} of {total}",
    "empty.title": "Waiting for matches...",
    "empty.description": "Matches will appear here as they are found",
    "errors.summaryFailed": "Failed to load matching summary",
    "errors.matchesFailed": "Failed to load matches",
    "errors.retry": "Retry"
  }
}
```

## 9. Performance Considerations

### 9.1 Polling Optimization
- Separate polling intervals for summary (4s) and matches (5s)
- Polling stops immediately on phase change
- Query keys include params to prevent unnecessary refetches

### 9.2 Rendering Optimization
- `useMemo` for product grouping in results table
- Session storage for expand/collapse state (prevents re-renders)
- Conditional rendering based on phase

### 9.3 Data Limits
- Default limit: 25 matches per page
- Pagination controls for larger result sets
- Lazy loading on demand

## 10. Testing Strategy

### 10.1 Unit Tests
- Hook polling behavior (intervals, enabled states)
- Component rendering for each state (loading, error, empty, populated)
- Filter interactions (score slider)
- Expand/collapse behavior

### 10.2 Integration Tests
- React Query data flow with mocked API
- Phase transitions and panel state changes
- Session storage persistence

### 10.3 E2E Tests (Playwright)
- Start job → matching phase → panel appears
- Progress cards update with live data
- Matches appear in table
- Evidence badges reflect status
- Panel collapses on phase advance

## 11. Known Limitations

### 11.1 Current Constraints
- No WebSocket streaming (polling only)
- No bulk operations on matches (delete/flag)
- No full evidence gallery (only badges)
- No match detail drawer (planned for future sprint)

### 11.2 Fallback Behavior
- If summary endpoint unavailable: show indeterminate progress
- If totals missing: use job percent as fallback
- If matches fail: show error but keep summary visible

## 12. Future Enhancements
- WebSocket streaming for real-time updates
- Match detail drawer with full evidence preview
- Bulk match operations (approve/reject/flag)
- Export matches to CSV
- Advanced filtering (by product, video, platform)
- Match quality analytics dashboard
