# Sprint 9 — Retire `vector-index` Service

**Status:** Proposal → Implementation → Verification → Cleanup\
**Owner:** Platform / Matching\
**Goal:** Remove the standalone **vector-index** microservice. Zero user-facing behavior change.

---

## 1) Rationale

- **Redundant layer:** `vector-index` is a thin wrapper over pgvector; vision services already write vectors to DB.
- **Latency & ops:** One less network hop, fewer containers to build/monitor.
- **Simplified ownership:** Eliminates a service with minimal benefit.
- **Reversible:** If QPS or reuse demands, we can re‑introduce a shared vector service later.

---

## 2) Scope (What changes)

**Remove**

- `services/vector-index/` (code, Dockerfile, requirements, handlers, tests, helpers).
- CI jobs & images for `vector-index` (build, test, push).
- Compose/K8s manifests & secrets for `vector-index`.
- Observability assets: dashboards, alerts, logs, SLOs for the service.

**Keep (unchanged)**

- DB schema for embeddings on `product_images` / `video_frames`.
- Writers: `vision-embedding` updates embeddings; `vision-keypoint` writes `kp_blob_path`.

---

## 3) High‑Level Design Change

**Before**

```
matcher ──HTTP──> vector-index ──DB──> Postgres (pgvector)
```

**After**

```
matcher ───────────────DB──────────────> Postgres (pgvector)
```

---

## 4) Detailed Tasks & Checklist (Actionable)

- Inventory calls to `vector-index` across repo.
- Ask services/consumers if they call `vector-index` directly.
- Remove `vector-index` service block from docker-compose.
- Delete envs, ports, healthchecks for `vector-index`.
- Remove `vector-index` build/test/publish workflows.
- Update monorepo matrix to exclude `services/vector-index`.
- Remove `vector-index` panels from dashboards.
- Delete alerts referencing `vector-index`.
- Remove `services/vector-index/**` from repo.
- Purge images from registry (7-day rollback window).
- Update docs 



---

