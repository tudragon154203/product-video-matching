# Sprint 5 – **Breaking Rename**

**Scope:** Rename 2 services across the monorepo and infrastructure. **No rollback, no backwards compatibility.**

- `Catalog Collector` → ``
- `Media Ingestion` → ``

This is a **breaking** sprint: all old names are removed from code, configs, CI/CD, observability, and docs. Deployments using old names will fail by design.

---

## 1) Objectives & Non‑Goals

**Objectives**

- Rename service code directories/packages and all references.
- Update container images, Compose/Helm/K8s manifests, env vars, and secrets.
- Update event producer IDs/metrics labels/dashboards/alerts.
- Update READMEs, diagrams, runbooks, onboarding docs.

**Non-Goals**

- Changing event **contracts** unless they contain old service names.
- Data migration/state backfill.

---

## 2) Impacted Assets (Authoritative List)

- **Repo paths**
  - `services/catalog-collector/` → `services/dropship-product-finder/`
  - `services/media-ingestion/` → `services/video-crawler/`
- **Package names**: `catalog_collector` → `dropship_product_finder`, `media_ingestion` → `video_crawler`
- **Docker**: image tags, compose keys, `container_name`
- **K8s/Helm**: deployment/service names, labels, selectors
- **CI/CD**: jobs, artifacts, env vars
- **Observability**: metrics labels, dashboards, alert rules
- **Docs**: diagrams, ADRs, runbooks, READMEs

---

## 3) Contracts & Events

- **Unchanged**: routing keys (`products.collect.request`, `videos.search.request`, etc.)
- **Change**: service name references in payloads, headers, logs, metrics

---

## 4) Step‑by‑Step Plan (Summary)

1. **Freeze window**: tạm dừng merge thay đổi liên quan routing keys/contracts.

2. **Code rename**:

   - `services/catalog-collector` → `services/dropship-product-finder`
   - `services/media-ingestion` → `services/video-crawler`
   - Cập nhật package/imports, `SERVICE_NAME`/entrypoints/consts.

3. **Containers & Orchestration**: cập nhật image names, docker‑compose service keys, `container_name`, healthchecks; rename K8s Deploy/Service/Ingress + labels/selectors.

4. **Messaging (RabbitMQ)**: tạo **queue/binding mới** cho consumers mới; **xóa** queue/binding cũ (không alias). Routing keys giữ nguyên trừ khi chứa tên cũ.

5. **CI/CD & Secrets**: cập nhật job names, artifact/image paths, registry, env var & secret prefixes theo tên mới.

6. **Docs**: cập nhật READMEs, runbooks, sơ đồ kiến trúc/onboarding.

7. **Verification (smoke/E2E)**:

   - Gửi `products.collect.request` → được **Dropship Product Finder** tiêu thụ và phát `products.images.ready`.
   - Gửi `videos.search.request` → được **Video Crawler** tiêu thụ và phát `videos.keyframes.ready`.
   - Nhận `image.embeddings.completed` + `video.embeddings.completed` → Matching chạy OK.

8. **Cleanup**: xóa images/queues/dashboards/projects cũ; đảm bảo repo không còn tham chiếu tên cũ.

---

## 12) One‑Page Changelog (for commit message)

```
BREAKING: Rename services
- Catalog Collector -> Dropship Product Finder
- Media Ingestion   -> Video Crawler
No rollback/back-compat. Updated repo paths, image names, queues, CI, and dashboards.
```

