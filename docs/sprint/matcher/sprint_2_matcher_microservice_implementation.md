# PRD - **Matcher** Microservice (Minimal MatchRequest; Repo‑Synced)

> Version: 1.2 (repo-synced)
> Owner: Tu Nguyen / PVM Team
> Service: `matcher`

---

## 1) Overview & Problem Statement
The **Matcher** ranks and verifies product-video pairs using multi‑signal vision similarity once embeddings & keypoints are ready. It reads vectors/keypoints from **Postgres** (pgvector‑style cosine search with a temp table), applies pair‑level scoring (embedding + keypoint signals; current keypoint step is a lightweight placeholder), and emits match results over the **RabbitMQ** topic exchange. It runs after upstream embedding + keypoint phases complete.

Key alignment with repo:
- Vector search creates a transient embeddings table and performs pgvector-style similarity with a robust Python/numpy fallback when needed.
- Messaging uses **RabbitMQ (aio_pika)** with a `product_video_matching` topic exchange, built‑in retry + DLQ handling via a common message handler.
- Config sources: service `.env` + global config (`main/libs/config.py`) for DB, broker, storage paths.

---

## 2) Goals (Must-haves)
- Retrieve product image → video frame candidates via vector similarity and produce **top‑K** shortlists per image.
- Compute pair scores (embedding + keypoint signals). Note: keypoint scoring is currently a lightweight placeholder, not full RANSAC.
- Publish contract-compliant events (**match.result**) and a terminal **matchings.process.completed** per job.
- Respect **MatchRequest** inputs and integrate cleanly with the event‑driven architecture (RabbitMQ + DLQ semantics).

### Non-Goals
- Generating embeddings/keypoints (upstream services).
- Rendering visual evidence (handled by evidence-builder).

---

## 3) Users & Stakeholders
- Main-API: orchestrates phases and dispatches matching.
- Evidence-Builder: consumes match results to render proof.
- Front-end / Client / n8n: displays job results and diagnostics.

---

## 4) Inputs, Outputs, Contracts (Repo-accurate)

### 4.1 Inputs - `match.request`
Minimal, authoritative schema (current):
- Required: `{ job_id: string, event_id: string (uuid) }`
- `additionalProperties: false`
- The service derives products and videos by querying DB with `job_id`. Thresholds and retrieval limits come from service `.env`; there is no job‑manifest override in code currently.

### 4.2 Outputs
- `match.result` (per accepted product‑video pair):
  - `job_id`, `product_id`, `video_id`
  - `best_pair { img_id, frame_id, score_pair }`
  - `score ∈ [0,1]`, `ts`
- `matchings.process.completed` (once per job): `{ job_id, event_id }`.
- Note: `job.failed` is not emitted by the matcher service at present; failures are retried and may be routed to DLQ by the common message handler.

Source of truth: contract JSON Schemas in `main/libs/contracts/contracts/schemas/`.

---

## 5) High-Level Flow
1. Receive `MatchRequest { job_id, event_id }` via RabbitMQ topic.
2. Query DB for products and videos associated with `job_id`.
3. Fetch product images and video frames with embeddings from Postgres.
4. Vector search: create a temp table for frame embeddings; run pgvector‑style cosine; select top‑K per image (fallback as needed).
5. Pair scoring: embedding similarity + keypoint placeholder produce `pair_score`.
6. Aggregate/accept: choose best pair and apply acceptance heuristics; compute final score with small boosts.
7. Emit `match.result` for accepted pairs.
8. Emit `matchings.process.completed { job_id, event_id }`.

---

## 6) Detailed Design

### 6.1 Components (as in repo)
- `matching_components/vector_searcher.py` — pgvector‑style search + temp table + numpy fallback.
- `matching_components/pair_score_calculator.py` — embedding + keypoint placeholder scoring with inliers threshold; not full RANSAC yet.
- `matching_components/match_aggregator.py` — acceptance heuristics and final score small boosts; no diversification/idempotency logic in code yet.
- `handlers/matcher_handler.py` — message I/O, lifecycle, validation.
- `embedding_similarity.py` — embedding cosine utilities (RGB/GRAY weighted).
- `config_loader.py` — env + global config loader; no job‑manifest derivation currently.
- `services/service.py` — orchestration: DB/Broker wiring, publish results, completion.
- `matching/__init__.py` — `MatchingEngine` combining the components.

### 6.2 Data Access & Storage
- Uses shared libs (`main/libs/common-py/...`) for DB and CRUD utilities. Postgres DSN and credentials come from global config.
- Entities: `product_images(img_id, emb_rgb, emb_gray, kp_blob_path, ...)`, `video_frames(frame_id, ts, emb_rgb, emb_gray, kp_blob_path, ...)`.

### 6.3 Scoring, Thresholds & Rules
- Defaults (from `.env.example`):
  - `RETRIEVAL_TOPK=20`, `SIM_DEEP_MIN=0.82`, `INLIERS_MIN=0.35`, `MATCH_BEST_MIN=0.88`, `MATCH_CONS_MIN=2`, `MATCH_ACCEPT=0.80`.
- Pair score weights (current implementation): `0.35*embedding + 0.55*keypoint + 0.10*edge` (edge is a lightweight proxy).
- Final score: best pair score plus small boosts for consistency and distinct images; clipped to `[0,1]`.
- Diversity/idempotency: not implemented in code yet; acceptance uses thresholds and simple consistency counts.

### 6.4 Concurrency & Scaling
- Parallelize per-product batches; geometric checks planned to be parallel per candidate.
- Back-pressure via max in‑flight messages (broker‑level); idempotency guard is TODO.

### 6.5 Messaging, Retries & DLQ
- Broker: **RabbitMQ** `product_video_matching` topic exchange.
- Retries: exponential backoff with capped delay via common handler; messages include `x-retry-count` headers; on exhaustion, sent to **DLQ** with failure metadata.
- Validation errors raise and are handled by the consumer; the matcher does not publish `job.failed` today.

---

## 7) Observability & Ops
- Logs: structured logs via common logger; defensive logging around fallbacks.
- Metrics: not instrumented in code yet; plan to track retrieval latency, pass‑rates, acceptance‑rates, runtime, DLQ counts.
- Health: no HTTP health endpoint; process health is inferred via connectivity to DB/Broker and logs.
- CI: `main/.github/workflows/ci-matcher.yml` runs lint + unit tests for matcher.

---

## 8) Security & Privacy
- No PII. DB/broker creds via least privilege. Strict schema validation on ingress.

---

## 9) Configuration (Env + Global)
- Global (`main/libs/config.py`): `POSTGRES_*`, `BUS_BROKER`, `DATA_ROOT_CONTAINER`, `LOG_LEVEL`.
- Service `.env`: `RETRIEVAL_TOPK`, `SIM_DEEP_MIN`, `INLIERS_MIN`, `MATCH_BEST_MIN`, `MATCH_CONS_MIN`, `MATCH_ACCEPT`.
- Feature flags: none in code today (no `ENABLE_GEOM_VERIFY`, `KEYPOINT_ALGO`).
- Idempotency: `event_id` is logged and propagated; persistence/guards are TODO.

---

## 11) Edge Cases & Deterministic Rules
- If `top_k` > available frames, use all available; thresholds still apply.
- If embeddings/keypoints missing, code uses conservative fallbacks (embedding: skip/0; keypoints: lightweight proxy) rather than fabricating confident scores.
- Diversification by video/image is not implemented.

---

## 12) API & Events (Routing Keys)
- Consume: `match.request` — payload `{ job_id, event_id }` (UUID format for `event_id`), `additionalProperties: false`.
- Produce: `match.result`, `matchings.process.completed`.
- All events include `job_id`; `event_id` passes through unchanged.

---

## 13) Acceptance Criteria (Testable)
1. Given a minimal `MatchRequest { job_id, event_id }`, the service retrieves products/videos from DB, performs vector search (or fallback), and can publish ≥1 `match.result` for seeded data.
2. Each `match.result` conforms to schema; `score ∈ [0,1]`, `best_pair.score_pair ∈ [0,1]`.
3. On completion, emit exactly one `matchings.process.completed { job_id, event_id }`.
4. Transient failures trigger retries; on max attempts, message lands in DLQ with failure metadata.
5. Idempotency guard on `event_id` is documented but not implemented; `job.failed` is not emitted by matcher.

---

## 14) TDD Workflow (Team Standard)
1. Write test first (RED) → 2. Minimal code (GREEN) → 3. Refactor.

---

## 15) Milestones & Deliverables
- M1 — Contracts & Skeleton: topics, schemas, `matcher_handler`, config load, schema validation, basic CI.
- M2 — Vector Retrieval & Pair Scoring: `vector_searcher`, `pair_score_calculator` placeholder, aggregation, unit tests.
- M3 — Geometric Verification & Rules (planned): RANSAC inliers, diversification, idempotency guard, metrics.
- M4 — Integration & CI: Contract tests, E2E with mock DB/broker, dashboards & alerts.

---

## 16) Open Questions
- Enforce `event_id` UUID strictly (current schema says yes) vs allow opaque strings? (Keep UUID to align with contracts.)
- Should we time‑bucket frames (ASR/chapters) to bias likely mentions?
- Diversification strength per creator/video vs recall.

---

## Appendix A — What's Implemented (Repo)
- Contracts / Schemas: `match_request.json` minimal `{ job_id, event_id }` with `additionalProperties=false`; `match_result`, `matchings_process_completed` present.
- Service wiring & handler: config loader, handler, service structure, Dockerfile, requirements; handler validates minimal request and runs matching.
- Matching components: `EmbeddingSimilarity`, `VectorSearcher` (temp‑table pgvector + fallback), `PairScoreCalculator` (placeholder with inliers‑driven proxy), `MatchAggregator`.
- Configs & thresholds: `.env.example` exposes matching thresholds; `config_loader.py` maps env + global config.
- Messaging infra: RabbitMQ wrapper with retries & DLQ; `event_id` is logged and passed through (idempotency guard is TODO).
- Tests/CI: unit tests under `services/matcher/tests/unit/**`; GitHub workflow `ci-matcher.yml` runs lint + unit tests.

**End of PRD**

