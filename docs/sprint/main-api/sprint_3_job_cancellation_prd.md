# Main API — Job Cancellation & Deletion PRD

## 1. Background & Problem
Operators have no supported way to stop a long-running job that is malfunctioning or no longer needed. When a job is abandoned it continues to fan out work across RabbitMQ, ties up GPU workers, and leaves partial data in Postgres and on disk. Similarly, there is no endpoint to delete a finished job and the large asset footprint (products, videos, embeddings, evidence) accumulates indefinitely. We need first-class cancel + delete flows exposed through `main-api` so orchestration can stop downstream workers and clean up persisted artifacts.

## 2. Goals
1. **Cancelable jobs** – provide an authenticated HTTP endpoint that marks a job as `cancelled`, purges queued work for that job from RabbitMQ, and broadcasts a `job.cancelled` event so workers stop gracefully.
2. **Deletable jobs** – provide an endpoint to delete a job (and all associated assets). If the job is running, delete first cancels it, waits for acknowledgement, then removes database rows and file artifacts.
3. **Idempotent + auditable** – repeated cancel/delete requests should be safe; state transitions should be logged with metadata (reason, operator, timestamps) while keeping DB changes minimal (e.g., a couple of new columns or JSON payloads in existing tables).
4. **Operational safety** – ensure we do not orphan worker processes, leak queues, or delete data needed for compliance. Provide metrics + alerts for cancel/delete usage.

## 3. Non-Goals
- Automatic job expiry/retention policies (future work).
- UI implementation for the FE console (separate ticket).
- Full workflow replay/rollback; cancel/delete only stop and remove work, they don't revert earlier effects such as upstream marketplace scraping.

## 4. Users & Use Cases
- **Ops Engineer**: Cancels a job after spotting a stuck segmentation worker so resources free up.
- **Customer Success**: Deletes a completed job containing test data at a customer's request.
- **Automated watchdog**: Future automation can call cancel if SLA thresholds fail.

## 5. Functional Requirements
### 5.1 Cancel Job Endpoint
- **Route**: `POST /jobs/{job_id}/cancel`
- **Payload (optional)**:
  ```json
  { "reason": "user_request", "notes": "customer asked to stop" }
  ```
- **Behavior**:
  1. Validate job exists. If already `completed`/`failed`/`cancelled`, return 200 with current state (idempotent).
  2. Update `jobs.phase` to `cancelled`. Store `cancelled_at` (timestamp) and optional `cancelled_by` columns if needed for quick querying; additional metadata (reason/operator notes) can live in `phase_events` payloads to avoid multiple schema changes.
  3. Publish `job.cancelled` event with payload `{ job_id, reason, requested_by }`.
  4. Purge RabbitMQ queues for outstanding job-specific tasks:
     - Use `job_id` correlation IDs to remove in-flight messages (requires new helper in `BrokerHandler` to iterate over queues: `products.collect.request`, `videos.search.request`, etc.) and drop ones matching `job_id`.
     - Clear internal delay/priority queues if any exist (documented in infra).
  5. Soft-stop main-api orchestrations: prevent future phase updates, block automatic match triggers, reject `phase_event` updates for the job.
  6. Return response:
     ```json
     {
       "job_id": "uuid",
       "phase": "cancelled",
       "cancelled_at": "...",
       "reason": "user_request"
     }
     ```
- **Idempotency**: Additional calls simply return the stored cancellation record without re-notifying RabbitMQ (guard via `jobs.phase`); response metadata loaded from latest `phase_events` payload.
- **Authorization**: Reuse existing auth or implement simple API key header (config-driven). Only privileged roles may cancel/delete.

### 5.2 Delete Job Endpoint
- **Route**: `DELETE /jobs/{job_id}`
- **Query/body flags**: `?force=true` to skip waiting if already cancelled/timeouts.
- **Behavior**:
  1. If job not found: return 404 (no-op). If a prior delete event exists in `phase_events`, return 200 idempotently.
  2. If job active (phase not in `completed|failed|cancelled`), implicitly invoke cancel flow. Wait for `job.cancelled` acknowledgement (see §6) or timeout with informative error.
  3. Delete data in transactional order (database + disk):
     - `matches`, `match_evidence`, `video_frames`, `product_images`, `job_videos`, `products`, `phase_events`, `jobs`.
     - Additional tables discovered via `DatabaseHandler` (e.g., job_asset tables). Provide view of cascades in tech spec.
  4. Remove files under `config.DATA_ROOT` tied to the job:
     - Product images/masks: `/data/products/{job_id}/...`
     - Video frames and derived evidence.
     - Use background task queue if deletion is expensive; API responds with `202 Accepted` if asynchronous cleanup.
  5. Emit `job.deleted` event for audit/log sync.
  6. Response example:
     ```json
     {
       "job_id": "uuid",
       "deleted_at": "...",
       "status": "deleted"
     }
     ```
- **Constraints**: Hard-delete only after verifying no downstream references (e.g., analytics). Provide optional `soft_delete_only` feature flag to keep metadata but mark as deleted.

### 5.3 Observability & Safety
- Log each cancel/delete with job_id, reason, operator, and impacted queues.
- Emit metrics:
  - `job_cancellations_total{status=success|error}`
  - `job_deletions_total`
  - `job_cancel_duration_seconds` (initiation → all queues cleared)
- Alert when cancellations fail to purge RabbitMQ (queue depth > 0 after N seconds).

### 5.4 Validation & Error States
- If RabbitMQ purge fails, mark job as `cancellation_pending` and retry via background worker; return 202 until completion.
- Protect against deleting jobs in `in_progress` without `force` flag (return 409).
- Provide enumerated `reason` field with fallback to `other`.

## 6. RabbitMQ & Worker Coordination
1. **New Event**: `job.cancelled`
   ```json
   { "job_id": "uuid", "reason": "user_request", "requested_by": "ops@pvm", "event_id": "uuid" }
   ```
   - All worker services subscribe and must drop in-flight work for the job, ack outstanding deliveries, and delete temporary files.
2. **Queue Purge Strategy**:
   - Extend `BrokerHandler` with `purge_job_messages(job_id)` that:
     - Uses `basic_get` loop to drain messages and check if `job_id` matches `body["job_id"]` or `correlation_id`.
     - Leaves other jobs untouched.
   - Compose file should expose RabbitMQ management credentials so we can call HTTP API for faster selective purge (optional).
3. **Ack Handling**:
   - Workers should publish `job.cancelled.ack` to confirm they stopped and cleaned up. `main-api` tracks ack count to unblock deletion.

## 7. Data Model Updates (Minimized)
- Add **at most two nullable columns** on `jobs`: `cancelled_at TIMESTAMP` and `deleted_at TIMESTAMP` for fast filtering/analytics. Optional `cancelled_by/deleted_by` columns can be appended if we need operator attribution, but keep additions lean.
- Store detailed metadata (reason, notes, operator email, request origin) inside `phase_events.payload` JSON (add JSONB column if needed, otherwise reuse existing structure). Insert `phase_events` rows with names `job.cancelled` / `job.deleted`.
- Reuse existing cascades for dependent tables; deletion endpoint still removes rows exactly as today (no new tombstone table). Audit logs remain external.
- `JobStatusResponse` sources timestamps from the new columns, falling back to latest `phase_events` entries if columns are null (for backward compatibility).

## 8. API Contracts
### 8.1 Cancel Job
```
POST /jobs/{job_id}/cancel
Headers: Authorization, Content-Type: application/json
Body: { "reason": "user_request", "notes": "optional string" }
Responses:
- 200: { job_id, phase: "cancelled", cancelled_at, reason, notes }
- 202: { job_id, phase: "cancellation_pending" } (if RabbitMQ purge still running)
- 404: if job unknown
- 409: if job already deleted
```

### 8.2 Delete Job
```
DELETE /jobs/{job_id}?force=true|false
Headers: Authorization
Responses:
- 200: { job_id, status: "deleted", deleted_at }
- 202: { job_id, status: "deletion_in_progress" } (async disk cleanup)
- 404: job not found
- 409: job in progress and force=false
```

## 9. System Flow
1. **Cancel Flow**:
   - Client → `main-api` cancel endpoint.
   - JobService validates job, updates DB, emits `job.cancelled`, purges RabbitMQ, returns result.
   - Workers receive event and stop processing (skip publishing downstream events, clean memory).
2. **Delete Flow**:
   - Client → delete endpoint.
   - Cancel (if needed) → wait for ack/timeouts.
   - Run DB transaction deleting all job-owned rows (wrap in stored procedure to maintain referential integrity).
   - Dispatch background task to delete files; emit `job.deleted` phase event (captures timestamp/operator).
   - Respond to client; optionally provide status endpoint `/jobs/{job_id}/deletion-status`.

## 10. Security & Permissions
- Require admin/service tokens for cancel/delete.
- Audit log entries stored (job_id, operator, action, timestamp, request_id).
- Rate-limit cancel/delete to prevent abuse.

## 11. Testing Plan
### Unit Tests
- JobManagementService: cancel updates DB, publishes `job.cancelled`, handles idempotency.
- BrokerHandler: selective purge removes only targeted messages.
- Database cleanup procedure removes all dependent rows in correct order.

### Integration Tests (FastAPI TestClient + test RabbitMQ)
- `POST /jobs/{id}/cancel` on running job returns 200 and sets phase.
- RabbitMQ queue contains multiple jobs; cancel drains only matching job_id.
- `DELETE /jobs/{id}` removes DB rows and file mocks; `GET /jobs/{id}` → 404.
- Error path: queue purge failure returns 202 + pending status.

### E2E (optional)
- Start job, seed fake worker listeners, hit cancel, verify workers receive `job.cancelled`.
- Start job, run delete; confirm files removed from tmp data dir.

## 12. Observability & Ops
- Dashboards show count of cancellations/deletions, mean durations, failure counts.
- Alerts:
  - Cancel pending >5 min.
  - Deletion tasks failing.
- Runbook updates: how to trigger cancel/delete, interpret logs, recover on partial failures.

## 13. Rollout Plan
1. Apply small migration adding `cancelled_at` / `deleted_at` (and optional `*_by`) columns plus JSON payload support on `phase_events` if missing. Deploy main-api with cancel endpoint hidden behind feature flag.
2. Update worker services to honor `job.cancelled` event before enabling endpoint in prod.
3. Enable deletion endpoint after verifying end-to-end cleanup (staging + canary).
4. Document procedures for ops + support teams.

## 14. Open Questions
- Should we support “pause” vs “cancel”? (not in scope).
- Do we need to archive evidence externally before deletion? (if yes, extend delete workflow).
- How do we handle jobs already mid-deletion when another delete request arrives? (proposal: return current status).

## 15. Implementation Notes & Touch Points
- **FastAPI layer (`services/main-api/api`)**: add routes + schemas for cancel/delete, enforce auth, surface phase changes in responses.
- **Service layer (`services/main-api/services/job/job_management_service.py`)**: implement `cancel_job` and `delete_job` orchestrations, reusing `DatabaseHandler` + `BrokerHandler`.
- **DatabaseHandler (`services/main-api/handlers/database_handler.py`)**: helpers to read/write cancellation metadata (use new `cancelled_at/deleted_at` columns + `phase_events` payloads) plus cascade delete routines and auditing hooks.
- **BrokerHandler**: helper to purge job-specific RabbitMQ messages and to publish `job.cancelled` / `job.deleted`.
- **Phase processing (`services/main-api/services/phase/phase_event_service.py`)**: ignore incoming events for cancelled/deleted jobs.
- **Infrastructure**: RabbitMQ policy or management API permissions for selective purge; data volume cleanup script under `scripts/cleanup_job_assets.py`.
