# Sprint 3 – Contract/Schema Revamp Plan (Project: Product–Video Matching)

> Objective: Enforce **single, strict** event contracts across all services (no legacy/fallback) and rebuild from a clean state by dropping and recreating DB tables where needed. All producers/consumers must conform exactly to the schemas in `libs/contracts/contracts/schemas`. End‑to‑end runs must validate via `contracts.validator` with **zero warnings** and **zero coercions**.

---

## 0) TL;DR

- **Single source of truth**: `libs/contracts/contracts/schemas/*.json`.
- **No legacy**: only the new schemas are accepted and emitted.
- **Drop DB**: No migration scripts; drop and recreate schema to match new contracts.
- **Producers** emit payloads that match schemas exactly.
- **Consumers** validate and **reject** non‑conforming payloads.
- **Docs & tests** mirror schemas verbatim; CI blocks divergence.

---

## 1) Scope

- **In scope**
  - Update JSON Schemas and wire `contracts.validator` at producer/consumer edges.
  - Drop and recreate database schema to align with new contracts.
  - Update producer/consumer code to match **only** the new schemas.
  - Update `CONTRACTS.md`, unit/integration/E2E tests, CI gates, and sample payloads.
- **Out of scope**
  - ML/model logic (embedding/matching remain unchanged).

---

## 2) Contract Changes (Authoritative Spec – final, detailed)

This section **fully specifies** the event shapes we accept after Sprint 3. All schemas use `additionalProperties: false` and are validated at producer **and** consumer edges.

### 2.1 Envelope & Messaging (applies to all topics)

- **Exchange**: `product_video_matching` (topic, durable)
- **Routing key = topic name** (see per‑event topics below)
- **Message metadata** (added by broker wrapper):
  - `correlation_id` (UUIDv4) – required
  - `timestamp` (ISO8601, UTC) – required
- **IDs**: non‑empty strings (UUIDv4 preferred for new entities)
- **Numbers**: floats ≤ 6 decimal places; integers within stated bounds
- **Timestamps**: seconds since video start (`ts`) or ISO8601 where specified

> Note: The envelope metadata is injected by our broker layer and **not** part of the JSON schema files. The JSON schema validates only the `payload` body we emit.

---

### 2.2 `products.collect.request` (v2 – strict)

**Topic**: `products.collect.request`

**Purpose**: Instruct `catalog-collector` to fetch product metadata and images using **English search queries**.

**Schema (authoritative)**

```json
{
  "type": "object",
  "required": ["job_id", "queries", "top_amz", "top_ebay"],
  "properties": {
    "job_id": {"type": "string", "minLength": 1},
    "queries": {
      "type": "object",
      "required": ["en"],
      "properties": {
        "en": {
          "type": "array",
          "items": {"type": "string", "minLength": 1},
          "minItems": 1,
          "maxItems": 10
        }
      }
    },
    "top_amz": {"type": "integer", "minimum": 1, "maximum": 100},
    "top_ebay": {"type": "integer", "minimum": 1, "maximum": 100}
  }
}
```

**Key rules**

- `industry` **removed** (not accepted).
- At least **one** English query must be provided; duplicates should be **de‑duplicated** client‑side before emit.
- `top_amz` and `top_ebay` cap the number of items per marketplace.

**Valid example**

```json
{
  "job_id": "job-7f9a2a19-7e6a-4bd1-9f8a-5b8e8c2e3e55",
  "queries": {"en": ["neck massager", "foot massager"]},
  "top_amz": 10,
  "top_ebay": 5
}
```

**Invalid examples (must be rejected)**

- Missing `queries.en`
- Using `industry` instead of `queries`
- Non‑array `queries.en` or empty strings in queries
- `top_amz`/`top_ebay` out of bounds

**Consumer obligations (catalog‑collector)**

- Read `queries.en` → choose 1..N queries to execute; log which queries were used
- Produce downstream: `products.image.ready` **per image** with valid local path

---

### 2.3 `videos.search.request` (v2 – strict)

**Topic**: `videos.search.request`

**Purpose**: Instruct `media-ingestion` to search & ingest videos per platform using **language‑keyed** query arrays.

**Schema (authoritative)**

```json
{
  "type": "object",
  "required": ["job_id", "industry", "queries", "platforms", "recency_days"],
  "properties": {
    "job_id": {"type": "string", "minLength": 1},
    "industry": {"type": "string", "minLength": 1},
    "queries": {
      "type": "object",
      "minProperties": 1,
      "properties": {
        "vi": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "zh": {"type": "array", "items": {"type": "string", "minLength": 1}}
      }
    },
    "platforms": {
      "type": "array",
      "minItems": 1,
      "items": {"type": "string", "enum": ["youtube", "bilibili"]}
    },
    "recency_days": {"type": "integer", "minimum": 1, "maximum": 365}
  }
}
```

**Key rules**

- `queries` **must be an object** keyed by language (e.g., `vi`, `zh`).
- If a platform doesn’t support a language, the consumer may ignore that key.
- `industry` remains for analytics/routing; **not** a query fallback.

**Valid example**

```json
{
  "job_id": "job-7f9a2a19-7e6a-4bd1-9f8a-5b8e8c2e3e55",
  "industry": "electronics",
  "queries": {"vi": ["máy massage cổ"], "zh": ["颈部 按摩器"]},
  "platforms": ["youtube", "bilibili"],
  "recency_days": 30
}
```

**Invalid examples (must be rejected)**

- `queries` as an array instead of object
- Unknown languages (additionalProperties are not allowed)
- Platform values outside the enum list
- `recency_days` ≤ 0 or > 365

**Consumer obligations (media‑ingestion)**

- Iterate by platform → select the correct language queries → execute search
- Produce downstream: `videos.keyframes.ready` → leads to `features.ready`

---

### 2.4 Downstream Events (strict enforcement, shapes unchanged)

The following contracts are **unchanged** but enforced strictly with `additionalProperties: false`. Producers/consumers must validate and reject malformed payloads.

#### 2.4.1 `products.image.ready`

- Emitted per product image with `product_id`, `image_id`, `local_path` (+ optional basic metadata)
- Triggers `vision-embedding` to compute `emb_rgb`, `emb_gray`

#### 2.4.2 `features.ready`

- Emitted when embeddings or keypoints are ready
- `entity_type ∈ {"product_image", "video_frame"}`; `id` references the image or frame id

#### 2.4.3 `videos.keyframes.ready`

- Emitted by `media-ingestion` after extracting frames
- Contains `video_id` and `frames[]` items with `{frame_id, ts, local_path}`

#### 2.4.4 `match.request` → `match.result` / `match.result.enriched`

- Matching pipeline unchanged; ensure `score ∈ [0,1]`, `ts` is seconds
- `match.result.enriched` adds `evidence_path`

---

### 2.5 Validation, Errors, and Rejections

- **Producer‑side**: Validate payloads against JSON Schemas **before** publish; on failure → **do not publish**; log error with `error_code=FATAL_2005` (`INVALID_CONFIGURATION`) and concise details.
- **Consumer‑side**: Validate on ingress; on failure → **reject** (ack + log error, do not retry) with `error_code=FATAL_2001` (`INVALID_EVENT_SCHEMA`).
- **Metrics**: increment `contracts_schema_validation_errors_total{topic=...}`
- **Logs**: include `job_id`, `topic`, `correlation_id`, `schema`, and the first failing path (JSON Pointer).

---

## 3) Implementation Plan

1. Update schemas in `libs/contracts/contracts/schemas`.
2. Drop existing database and recreate tables as per new schema requirements.
3. Update `CONTRACTS.md` examples to match schemas exactly.
4. Modify producers (`main-api`) to emit only valid v2 payloads.
5. Modify consumers (`catalog-collector`, `media-ingestion`) to accept only valid v2 payloads.
6. Add schema validation at producer emit and consumer ingress.
7. Update and expand unit, integration, and E2E tests.
8. Configure CI to fail on schema validation errors.

---

## 4) Acceptance Criteria

- ✅ Producers emit **only** v2 payloads.
- ✅ Consumers accept **only** v2 payloads.
- ✅ Database matches new schema (freshly created).
- ✅ `contracts.validator` passes across all test stages.
- ✅ Zero schema‑validation errors for 24h in staging.

