# Spec: `app/[locale]/jobs/[jobId]` – Products & Videos Panels (gridless)

## 1) Feature Goal

- Show **Products** (left) and **Videos** (right) in two parallel panels, **gridless** (list-style), grouped respectively by **source** and **platform**.
- Each panel uses **independent pagination** with **10 items/page**.
- Route is localized: `app/[locale]/jobs/[jobId]`. All labels via `next-intl`.
- Timezone rendering: **GMT+7** for timestamps.

---

## 2) Data Contracts (frontend expectations)

### 2.1 `ProductDetail`

```ts
{
  product_id: string,
  src: string,          // e.g., "amazon", "ebay"
  asin_or_itemid?: string,
  title: string,
  brand?: string,
  url: string,
  created_at?: string,  // ISO
  image_url_main?: string, // recommended to simplify UI (if absent, show placeholder)
  image_count?: number
}
```

### 2.2 `VideoDetail`

```ts
{
  video_id: string,
  platform: string,     // e.g., "youtube", "tiktok"
  url: string,
  title: string,
  duration_s: number,
  published_at?: string, // ISO
  created_at?: string,   // ISO
  frame_count?: number,
  thumbnail_url?: string // optional convenience
}
```

### 2.3 Paginated List Response

```ts
{
  items: T[],
  total: number,
  limit: number, // requested limit
  offset: number // requested offset
}
```

---

## 3) API Endpoints (paginated)

- `GET /jobs/{jobId}/products?limit=10&offset=0` → `{ items: ProductDetail[], total, limit, offset }`
- `GET /jobs/{jobId}/videos?limit=10&offset=0` → `{ items: VideoDetail[], total, limit, offset }`
- `GET /status/{jobId}` → `{ phase: string, percent?: number, ... }` (for optional polling)

> Notes
>
> - Products and Videos panels fetch independently (separate query keys and pagination state).
> - If `image_url_main` or `thumbnail_url` isn’t provided, the UI shows a neutral placeholder.

---

## 4) UX & Interaction

### 4.1 Grouping

- **Products** grouped by `src`.
- **Videos** grouped by `platform`.
- Group header shows label (badge) and item count within that group.

### 4.2 Item Display (gridless rows)

- **Product row**: square thumbnail (56–72px), full title (link opens in new tab), optional brand/asin/date below in small text.
- **Video row**: title (link), duration formatted `mm:ss`, optional published\_at (GMT+7) and frame\_count as meta.

### 4.3 Pagination (per panel)

- Limit = 10, `offset` changes in steps of 10.
- Prev/Next buttons; disabled when at bounds.
- Panels paginate independently (changing one does not affect the other).
- (Optional) Sync to URL query: `?p_offset=..&v_offset=..`.

### 4.4 States

- Loading: skeleton rows per panel; non-blocking.
- Error: inline error with a **Retry** button for that panel.
- Empty: text message (see i18n keys).
- Partial: one panel can render while the other is empty/error.

### 4.5 Polling / Phase Awareness (optional)

- Poll `GET /status/{jobId}` every 5–10s while `phase === "collection"`.
- On phase change out of `collection`, stop polling and (optionally) stop auto-refetch.

---

## 5) Component Tree (App Router + shadcn/ui)

```
app/
  [locale]/
    jobs/
      [jobId]/
        page.tsx                # JobDetailsPage

components/jobs/
  JobSplitView.tsx              # Layout wrapper: two flexible columns (gridless)

  # Left: Products panel
  ProductsPanel/
    index.tsx                   # Exports ProductsPanel (compose children below)
    ProductsPanel.tsx           # Fetch + state (limit/offset) + grouping
    ProductGroup.tsx            # Header for a source group (badge + count)
    ProductItemRow.tsx          # Single product row (thumb, title link, meta)
    ProductsPagination.tsx      # Prev/Next for products
    ProductsSkeleton.tsx        # Skeleton list for loading
    ProductsEmpty.tsx           # Empty state
    ProductsError.tsx           # Error state with Retry

  # Right: Videos panel
  VideosPanel/
    index.tsx                   # Exports VideosPanel (compose children below)
    VideosPanel.tsx             # Fetch + state (limit/offset) + grouping
    VideoGroup.tsx              # Header for a platform group (badge + count)
    VideoItemRow.tsx            # Single video row (title link, duration, meta)
    VideosPagination.tsx        # Prev/Next for videos
    VideosSkeleton.tsx          # Skeleton list for loading
    VideosEmpty.tsx             # Empty state
    VideosError.tsx             # Error state with Retry

  # Shared bits
  PanelHeader.tsx               # Title + optional count and description
  InlineBadge.tsx               # src/platform badge
  PanelSection.tsx              # Thin card/section wrapper (shadcn Card)
  ListDivider.tsx               # Divider between groups
  LinkExternalIcon.tsx          # Small icon for external links

lib/api/services/
  result.api.ts                 # getJobProducts, getJobVideos (paginated)
  status.api.ts                 # getJobStatus (phase)

hooks/
  usePaginatedList.ts           # Generic hook: {offset, setOffset, next, prev, canPrev, canNext}
  useJobStatusPolling.ts        # Polls status; exposes phase, percent, isCollecting

lib/utils/
  formatDuration.ts             # seconds -> mm:ss
  formatGMT7.ts                 # ISO -> localized string in GMT+7
  groupBy.ts                    # Generic grouping helper

messages/
  jobs.en.json, jobs.vi.json    # i18n strings
```

---

## 6) Component Responsibilities & Props

### 6.1 `page.tsx` (JobDetailsPage)

- Reads `[jobId]` and `[locale]`.
- Layout: `<JobSplitView left={<ProductsPanel jobId={..}/>} right={<VideosPanel jobId={..}/>} />`
- (Optional) mounts `useJobStatusPolling(jobId)` and passes `isCollecting` to panels to toggle auto-refetch.

### 6.2 `JobSplitView`

- Props: `{ left: ReactNode; right: ReactNode; }`
- Two-column flexible layout with `flex` (no grid). Stacks vertically on small screens.

### 6.3 `ProductsPanel`

- Props: `{ jobId: string; isCollecting?: boolean }`
- Internal state: `limit = 10`, `offset`, `isFetching`.
- Effects: fetch products; if `isCollecting`, set an interval to refetch.
- Renders: `PanelHeader`, groups (`ProductGroup` + `ProductItemRow[]`), `ProductsPagination`.

### 6.4 `ProductGroup`

- Props: `{ src: string; count: number }`
- Renders group label using `InlineBadge`.

### 6.5 `ProductItemRow`

- Props: `{ product: ProductDetail }`
- Opens `product.url` in a new tab (with external icon). Shows thumb, title, meta.

### 6.6 `ProductsPagination`

- Props: `{ total: number; limit: number; offset: number; onPrev(): void; onNext(): void }`
- Calculates bounds: `canPrev = offset > 0`, `canNext = offset + limit < total`.

### 6.7 `VideosPanel`

- Props: `{ jobId: string; isCollecting?: boolean }`
- Mirror of `ProductsPanel` but for videos.

### 6.8 `VideoGroup`

- Props: `{ platform: string; count: number }`

### 6.9 `VideoItemRow`

- Props: `{ video: VideoDetail }`
- Opens `video.url` in a new tab; shows title, `formatDuration(video.duration_s)`, optional meta.

### 6.10 Shared components

- `PanelHeader`: `{ title: string; subtitle?: string; count?: number }`
- `InlineBadge`: `{ text: string }`
- `PanelSection`: thin card container (padding, soft shadow).
- `ListDivider`: simple horizontal rule between groups.

---

## 7) Hooks

### 7.1 `usePaginatedList`

```ts
function usePaginatedList(initialOffset = 0, limit = 10) {
  const [offset, setOffset] = useState(initialOffset)
  const next = (total: number) => setOffset(o => (o + limit < total ? o + limit : o))
  const prev = () => setOffset(o => Math.max(0, o - limit))
  const canPrev = offset > 0
  const canNext = (total: number) => offset + limit < total
  return { offset, setOffset, limit, next, prev, canPrev, canNext }
}
```

### 7.2 `useJobStatusPolling(jobId)`

- Polls `/status/{jobId}` every 5–10s.
- Returns `{ phase, percent, isCollecting }` where `isCollecting = phase === 'collection'`.

---

## 8) Services (API layer)

```ts
// result.api.ts
export async function getJobProducts(jobId: string, { limit = 10, offset = 0 }) { /* fetch + zod parse */ }
export async function getJobVideos(jobId: string, { limit = 10, offset = 0 }) { /* fetch + zod parse */ }

// status.api.ts
export async function getJobStatus(jobId: string) { /* fetch status */ }
```

- Use a centralized `client.ts` with error handling and base URL.
- Zod schemas mirror `ProductDetail`, `VideoDetail`, and list payload.

---

## 9) Utilities

- `formatDuration(seconds: number): string` → `mm:ss` (pad zeros).
- `formatGMT7(iso?: string): string` → returns localized date/time in GMT+7 (safely handles nulls).
- `groupBy<T, K extends string>(arr: T[], key: (t: T) => K): Record<K, T[]>`.

---

## 10) i18n Keys (`messages/jobs.en.json` / `jobs.vi.json`)

```json
{
  "title": "Job Results",
  "products": {
    "panelTitle": "Products",
    "empty": "No products collected.",
    "source": "Source",
    "openLinkAria": "Open product on {src}",
    "paginatePrev": "Previous",
    "paginateNext": "Next"
  },
  "videos": {
    "panelTitle": "Videos",
    "empty": "No videos collected.",
    "platform": "Platform",
    "openLinkAria": "Open video on {platform}",
    "paginatePrev": "Previous",
    "paginateNext": "Next"
  },
  "meta": {
    "brand": "Brand",
    "asin": "ASIN/Item ID",
    "publishedAt": "Published",
    "createdAt": "Created"
  },
  "errors": {
    "loadFailed": "Failed to load data.",
    "retry": "Retry"
  }
}
```

---

## 11) Accessibility

- External links include descriptive `aria-label` (from i18n with source/platform name).
- Pagination buttons include `aria-current="page"` on the active page (if page numbers are later added). For now, ensure labels and disabled states are present.

---

## 12) Telemetry (optional)

- `open_product_link`: `{ jobId, src, product_id }`
- `open_video_link`: `{ jobId, platform, video_id }`
- `paginate_products`: `{ jobId, offset, limit }`
- `paginate_videos`: `{ jobId, offset, limit }`

---

## 13) Acceptance Criteria (AC)

1. `/[locale]/jobs/[jobId]` renders two side-by-side panels without CSS grid.
2. Products are grouped by `src`; videos by `platform`.
3. Each item row shows required fields and opens the correct external link in a new tab.
4. Each panel paginates independently with 10 items/page.
5. Loading, error, and empty states behave correctly per panel.
6. (Optional) While phase is `collection`, panels auto-refetch; they stop after phase changes.
7. All labels are localized; timestamps display in GMT+7.

---

## 14) Implementation Notes

- Prefer shadcn/ui `Card`, `Badge`, `Button`, and `Separator` for a clean, lightweight look.
- Keep item rows compact (thumb 56–72px, ellipsis for long titles, focus style on links).
- Defer heavy thumbnails with `loading="lazy"`.
- If back-end can’t supply `image_url_main`/`thumbnail_url` yet, ship with placeholders and file a follow-up task.

