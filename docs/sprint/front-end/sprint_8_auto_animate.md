# Sprint 8 – Front-End: Auto‑Animate Integration (Specs)

## Objective
- Add smooth, low‑friction animations for list changes across Product/Video panels and Job Sidebar, improving perceived responsiveness during realtime updates (polling) and pagination.
- Use a lightweight, zero‑config library to minimize code churn while preserving performance and accessibility.

## Approach (Library Choice)
- Primary: @formkit/auto-animate
  - Rationale: drop‑in, no choreography needed, FLIP‑style layout transitions for insert/remove/reorder; minimal bundle cost; ideal for TanStack Query polling.
- Alternatives (out of scope for this sprint): Motion (Framer Motion) for bespoke/staggered choreography and React Transition Group for CSS‑driven enter/exit. Keep in mind for future enhancements.

## Scope
- Panels
  - VideosPanel: animate item insertions/removals within each platform group’s item container.
  - ProductsPanel: animate item insertions/removals within each source group’s item container.
  - CommonPanelLayout sections: optional group header transitions kept subtle (no crossfade of titles in this sprint).
- Sidebar
  - JobSidebar job list: animate changes as jobs are added, phase changes reorder, or list refetches.
- Shared UI
  - Pagination lists (CommonPagination consumers): animate page list content swaps to reduce “snap”.
  - Thumbnails: optional subtle opacity reveal when image load completes (retain current skeleton behavior; keep subtle).

## Non‑Goals
- Complex staggered choreography or shared‑element transitions.
- Animations for every micro‑interaction (buttons, toggles) beyond lists and thumbnails.
- Virtualized lists.

## UX/Animation Guidelines
- Motion type: subtle fade + transform for list items; no aggressive slide distances.
- Duration: 150–220ms for insert/remove; 200–250ms for list reorders; consistent across app.
- Easing: standard ease‑out for enter, ease‑in for exit.
- Direction: items appear in place; avoid large translation to prevent “jumping”.
- Reduced motion: respect `prefers-reduced-motion` (disable or simplify animations).
- Pagination: transitioning pages should feel like content replacement, not heavy motion; a brief cross‑fade is acceptable.

## Integration Guidelines
- Apply auto‑animate to the immediate parent container of list items (the element that receives children insert/remove).
- Ensure stable React keys:
  - Videos: `video_id`
  - Products: `product_id`
  - Jobs: `job_id`
- Avoid structural churn: keep a stable wrapper around list items; don’t re‑wrap the list per render.
- Polling compatibility: auto‑animate runs on DOM mutations; ensure refetches update in‑place, not via full remount.
- Pagination compatibility: when offset/limit changes, allow a subtle content transition; avoid animating skeleton placeholders as “enter/exit” during quick page flips.

## Config & Feature Flag
- Add a global flag to toggle animations at runtime:
  - Env: `NEXT_PUBLIC_ENABLE_ANIMATIONS` (`true` default in dev, `true` in prod unless issues observed).
  - The Providers layer or a small utility can read the flag and opt‑out early (no auto‑animate initialization).
- Respect `prefers-reduced-motion`: override to disable animations when the OS setting requests reduced motion.

## Affected Components (Files)
- Videos list
  - `services/front-end/components/jobs/VideosPanel/VideosPanel.tsx` (per‑platform item container)
  - `services/front-end/components/jobs/VideosPanel/VideoItemRow.tsx` (no direct changes; ensure stable keys only)
- Products list
  - `services/front-end/components/jobs/ProductsPanel/ProductsPanel.tsx` (per‑source item container)
  - `services/front-end/components/jobs/ProductsPanel/ProductItemRow.tsx` (ensure stable keys)
- Sidebar
  - `services/front-end/components/job-sidebar/job-list-card.tsx` (list container)
  - Related item rows under `job-sidebar/`
- Shared
  - `services/front-end/components/CommonPanel/*` (only if a shared list wrapper exists)
  - `services/front-end/components/common/ThumbnailImage.tsx` (optional subtle opacity reveal upon load complete)

## Implementation Plan (No Code in Spec)
1) Dependency
   - Add @formkit/auto-animate to front-end package.
2) Utility
   - Create a tiny helper to initialize auto‑animate with default timings/easing and respects feature flag + reduced motion.
   - Expose configuration knobs (duration, easing) in one place.
3) Integrations
   - VideosPanel: attach to the container that maps `videos.map(...)` within each platform section.
   - ProductsPanel: attach to the container that maps items within each source section.
   - JobSidebar: attach to the jobs list container so polling updates animate.
   - Pagination lists: attach to the list container below `CommonPanelLayout` where page content is replaced.
   - Thumbnails: add subtle opacity reveal on successful image load (do not animate size; preserve fixed 120×120 to avoid layout shift).
4) Reduced Motion & Flag
   - Detect `prefers-reduced-motion` and short‑circuit initialization.
   - Read `NEXT_PUBLIC_ENABLE_ANIMATIONS`; if false, do nothing.
5) Guardrails
   - Ensure item keys are stable and unique.
   - Avoid mounting/unmounting the entire list wrapper on refetch; keep the same parent element.
   - Suppress excessive animation during rapid refetch sequences by relying on library’s internal throttling; if needed, debounce reflow triggers.

## Accessibility
- Honor `prefers-reduced-motion` across all animated surfaces.
- Maintain focus order and do not animate focus outlines.
- Avoid motion that implies directional meaning not present in data.

## Performance
- Lists are limited (10 items/page); expect negligible overhead.
- Ensure no expensive reflows from measuring off‑screen elements; keep fixed thumbnail sizes to prevent layout shift.
- Monitor paint timings in DevTools; ensure < 16ms frame budget typically.

## QA / Acceptance Criteria
- When new videos arrive during collection, items ease in smoothly without layout jump.
- When switching pages, the previous items fade out and new items fade in without jank or double‑animation of skeletons.
- JobSidebar updates (new job, phase change reorder) animate smoothly; no flicker on group headers.
- Thumbnails reveal smoothly once loaded; skeletons vanish without abrupt pop.
- With `prefers-reduced-motion` enabled, no list animations occur.
- Toggling the feature flag disables all animations app‑wide.

## Testing Plan
- Manual
  - Start a job, keep Job Details open, observe VideosPanel while items stream in.
  - Paginate forward/back on Videos/Products; confirm smooth transitions.
  - Simulate slow network to observe skeleton → content transition.
  - Toggle OS reduced motion; verify animations are disabled.
- Automated (follow-up)
  - E2E sanity checks: presence of animated container attribute/classes; visual regression optional.

## Rollout & Monitoring
- Ship behind `NEXT_PUBLIC_ENABLE_ANIMATIONS` flag.
- Dogfood in dev/staging; watch for any layout thrash or performance regressions.
- If issues appear, disable via env without code rollback.

## Risks & Mitigations
- Excessive animation on frequent polling: rely on low‑intensity transitions; debouncing is available if needed.
- Structural remounts suppress animation: ensure list wrappers remain stable.
- Accessibility concerns: reduced motion honored; flag fallback.

## Future Enhancements (Post‑Sprint)
- Motion (Framer Motion) for staggered item reveals and panel‑level transitions.
- Shared‑element transitions for thumbnails/keyframes.
- Animate count badges and headers with number tweening (respect reduced motion).

