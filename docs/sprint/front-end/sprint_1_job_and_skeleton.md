# Frontend Microservice – Product Spec (Sprint 1)

**Name:** `frontend`

**Tech Stack:** Next.js (App Router) • TypeScript • TailwindCSS • shadcn/ui (Radix UI) • TanStack Query • Zod • ESLint/Prettier • Jest/RTL • Playwright

**Context:** This service is the UI layer for the existing *main API* (polling, no SSE). Timezone is **GMT+7** for all presented timestamps.

---

## 1) Goals & Non‑Goals

**Goals**

- Provide dashboards and tools to monitor jobs and status in Sprint 1.
- Offer fast, accessible, and responsive UI for operators.
- Strict typing and runtime validation of API responses.
- Simple theming (light/dark) and reusable component system.

**Non‑Goals**

- No server-side business logic beyond UI rendering and API orchestration.
- No SSE/WebSocket in v1 (polling only).
- No authentication/roles in Sprint 1.

---

## 2) Users & Use Cases

**Primary users:** Operators / Engineers.

**Use cases (Sprint 1):**

- Start a job via UI.
- Monitor status/progress of jobs.

---

## 3) Information Architecture & Routes (App Router)

- `/` → Overview: recent jobs, quick stats.
- `/jobs` → Start new job + (later) list jobs.
- `/jobs/[jobId]` → Job detail (Summary tab only in Sprint 1).

**Query Params (future):** `?q=`, `?status=`, `?limit=`, `?offset=`, etc.

---

## 4) API Integration (Contracts)

**Base URL**: `process.env.NEXT_PUBLIC_API_BASE_URL`

### 4.1 Source-of-truth (read from codebase)

**Endpoints used in Sprint 1** — exact shapes inferred from `repomix-output.md`:

#### POST `/start-job`

- **Purpose**: Start a new matching job.
- **Request Body (JSON)** — *all fields required in current code*:
  - `query` *(string)* — original user query.
  - `top_amz` *(integer)* — number of top Amazon products to collect.
  - `top_ebay` *(integer)* — number of top eBay products to collect.
  - `platforms` *(string[])* — target video platforms. Observed values: `"youtube"`, `"douyin"`, `"tiktok"`, `"bilibili"`.
  - `recency_days` *(integer)* — time window (days) for video search.
- **Response 200 (JSON)**:
  - `job_id` *(string)* — generated UUID.
  - `status` *(string)* — always `"started"` on success.
- **Failure**: `500` with `{ detail: string }`.
- **Side-effects**: stores job with initial `phase="collection"`; publishes product-collection & video-search events using provided parameters.

#### GET `/status/{job_id}`

- **Purpose**: Retrieve current status snapshot for a job.
- **Response 200 (JSON)**:
  - `job_id` *(string)*
  - `phase` *(string)* — observed values in code: `"unknown"`, `"collection"`, `"feature_extraction"`, `"matching"`, `"evidence"`, `"completed"`, `"failed"`.
  - `percent` *(number)* — derived from phase (mapping: collection→20, feature_extraction→50, matching→80, evidence→90, completed→100, failed→0).
  - `counts` *(object)* — `{ products: number, videos: number, images: number, frames: number }`.
  - `updated_at` *(ISO datetime | null)* — last DB activity for this job.
- **Not found job**: returns `phase="unknown"`, `percent=0.0`, counts all `0`, `updated_at=null` (HTTP 200).

### 4.2 Polling (UI convention)

- Poll `/status/{job_id}` every **5s**.
- Stop polling on terminal phases: **`completed`** or **`failed`**.
- Display timestamps in **GMT+7** (UI formatting only).

---

## 5) UI/UX Guidelines

- **Design system**: shadcn/ui components (Button, Card, Tabs, Table, Progress, Toast, Tooltip).
- **Layout**: Sidebar + topbar; grid for content.
- **States**: loading skeletons; empty; error.
- **Accessibility**: Radix primitives; keyboard nav; aria labels.
- **Theming**: light/dark via CSS variables (tailwind + `next-themes`).

---

## 6) Components (Sprint 1)

- **JobStatusCard**: id, status, progress, timestamps, CTA.
- **StatsKPI**: small cards for counts (jobs started, jobs running).
- **StartJobForm**: simple form to trigger `POST /start-job`.
- **ProgressBar**: % with label.
- **Toast/ConfirmDialog**: for actions and errors.

---

## 7) Data Models (TS/Zod – Sprint 1)

> High-level shapes for UI validation (align with backend fields).

```ts
import { z } from "zod";

export const Phase = z.enum([
  "unknown",
  "collection",
  "feature_extraction",
  "matching",
  "evidence",
  "completed",
  "failed",
]);

export const JobStatus = z.object({
  job_id: z.string(),
  phase: Phase,
  percent: z.number(),
  counts: z.object({
    products: z.number(),
    videos: z.number(),
    images: z.number(),
    frames: z.number(),
  }),
  updated_at: z.string().nullable(),
});

export const StartJobResponse = z.object({
  job_id: z.string(),
  status: z.literal("started"),
});

export const StartJobRequest = z.object({
  query: z.string(),
  top_amz: z.number().int(),
  top_ebay: z.number().int(),
  platforms: z.array(z.enum(["youtube","douyin","tiktok","bilibili"])),
  recency_days: z.number().int(),
});
```

---

## 8) State Management

- **TanStack Query** for server state (queries, mutations, caching, polling, retries, devtools).
- **Local/URL state** minimal in Sprint 1.

---

## 9) Sprint 1 Deliverables

- Skeleton Next.js project with Tailwind + shadcn/ui setup.
- Dockerfile + CI skeleton.
- Health page hitting `/health` and displaying system status.
- `/jobs` page with StartJobForm.
- `/jobs/[jobId]` page showing job status, progress bar, polling.
- Zod validation for responses.

---

## 10) Directory Structure (App Router – Sprint 1)

```
front-end/
 ├─ app/
 │   ├─ layout.tsx
 │   ├─ page.tsx               # /
 │   ├─ jobs/
 │   │   ├─ page.tsx           # /jobs
 │   │   └─ [jobId]/page.tsx   # /jobs/[jobId]
 │   └─ health/page.tsx
 ├─ components/
 │   ├─ JobStatusCard.tsx
 │   ├─ StartJobForm.tsx
 │   └─ ProgressBar.tsx
 ├─ lib/
 │   ├─ api.ts
 │   ├─ zod/job.ts
 │   └─ time.ts
 ├─ styles/
 │   └─ globals.css
 ├─ tailwind.config.ts
 ├─ eslint.config.mjs
 ├─ Dockerfile
 └─ package.json
```

---

## 11) Milestones (Sprint 1)

**Day 1–2:**

- Scaffold Next.js + TS + Tailwind + shadcn; base layout; env wiring; Dockerfile; CI skeleton.
- Health page + fetch `/health`.

**Day 3–4:**

- Implement StartJobForm on `/jobs`.
- Implement `/jobs/[jobId]` detail; polling `/status/{job_id}`.

**Day 5:**

- Add JobStatusCard for job detail.
- Error states, Zod validation, toasts.

---

## 12) Acceptance Criteria (Sprint 1)

- Health page shows backend status.
- `/jobs` allows user to start job.
- `/jobs/[jobId]` shows job status, progress polling.
- All API responses validated with Zod.
- Light/dark theme supported.
