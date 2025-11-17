# Sprint 14 – Completion Threshold For Progress Manager

## Overview
- **Owner:** Vision Platform Core
- **Last Updated:** 2025-11-17  
- **Scope:** Vision services (`vision-embedding`, `vision-keypoint`, `product-segmentor`, `video-crawler`)

## Problem Statement
Progress completion events are only emitted when `done == expected`. Any mismatch between announced asset counts and successfully processed assets (e.g., filtering bad frames, upstream retries) permanently blocks `*.completed` and `*.masked.batch` events. This causes:
- Jobs stuck in the feature extraction phase even though >80% assets are ready.
- Event-driven consumers (matcher, evidence-builder) never triggered, forcing manual intervention.
- Missing recovery path when crawling steps finish with shortfalls.

## Goals
1. Introduce a configurable completion threshold so jobs can advance once the majority of assets are processed.
2. Expose the threshold in shared configuration and infra `.env` so all services and tests share the same value.
3. Preserve partial completion signaling to downstream consumers (`has_partial_completion` stays `True` when `done < expected`).

## Non-Goals
- Changing per-service batching semantics.
- Modifying downstream consumers’ retry logic beyond receiving earlier completion events.
- Tracking failed asset counts (still reported as `0` placeholders).

## Functional Requirements
1. `JobProgressManager` MUST treat a phase as complete when `done >= expected * COMPLETION_THRESHOLD_PERCENTAGE / 100`.
2. `COMPLETION_THRESHOLD_PERCENTAGE` defaults to `90` and is clamped to `[0, 100]`.
3. The new setting is available through:
   - `infra/pvm/.env` (for Compose/default dev environment),
   - `libs/config.Config.COMPLETION_THRESHOLD_PERCENTAGE`.
4. Batch events (`products.images.masked.batch`, `video.keyframes.masked.batch`, etc.) are emitted immediately once the threshold is met.
5. `has_partial_completion` remains `True` whenever `done < expected`, even if the threshold condition passes.

## Technical Notes
- `JobProgressManager` now reads the threshold from global config with an environment fallback.
- `BaseJobProgressManager` owns a helper to determine whether the threshold is satisfied; both `update_job_progress` and `update_expected_and_recheck_completion` reuse it.
- Progress comparisons use floating-point math (e.g., `expected=20`, threshold `0.9` → `done >= 18`). For small batches, integer rounding effectively keeps the previous behavior.
- Infra config changes:
  - `infra/pvm/.env` and `.env.example` expose `COMPLETION_THRESHOLD_PERCENTAGE`.
  - `libs/config.Config` surfaces the same field so every service inherits the value without duplicating env parsing.
- Vision services automatically pick up the new behavior because they already instantiate `JobProgressManager`; no service-level patches are required unless a service wants to override the threshold locally.

## Testing
- New unit tests cover:
  - Auto-completion triggered exactly at the configured threshold.
  - Guard rails preventing premature completion.
  - Recheck path when the expected count is updated later.
- Existing completion publisher tests remain valid because `has_partial_completion` still reflects strict equality.

## Rollout
1. Update infra `.env`/`.env.example`, restart Compose stack to reload the new variable.
2. No DB migrations required.
3. Monitor job metrics during the first sprint to ensure no regressions (look for early `*.completed` events with `has_partial_completion=true` and verify downstream services handle them).
4. If future sprints need different tolerance levels (e.g., for flaky crawlers), adjust the percentage in a single place and redeploy; no code change required.
