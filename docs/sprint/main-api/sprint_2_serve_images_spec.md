# Image Serving via `main-api` — Specs (AC & TDD Focus)

## 1) Overview
**Goal**: Front‑end loads product/video images over HTTP from `main-api`, which serves files from a mounted data directory. No front‑end file access or copying to `public/` is required.

- **Static mount prefix**: `/files`
- **Data root inside container**: `config.DATA_ROOT` (e.g., `/app/data`)
- **Host ↔ container volume**: `${DATA_ROOT_HOST} : ${DATA_ROOT_CONTAINER}` (already in docker‑compose)
- **Front‑end base URL**: `NEXT_PUBLIC_API_BASE_URL` (e.g., `http://localhost:8888`)

## 2) Scope & Non‑Goals
### In Scope
- Mounting and exposing static files at `/files` from `config.DATA_ROOT`.
- Returning a **public `url`** for each image in API responses (derived from `local_path`).
- Front‑end uses the `url` to render images.
- Basic caching and CORS headers suitable for local dev and prod.

### Out of Scope / Non‑Goals
- Image transformations (resize, watermark, thumbnail).
- AuthN/AuthZ and signed URLs.
- CDN integration.
- Directory listing / file uploads.

## 3) Definitions & Constraints
- **`local_path`**: Absolute path (inside container) to the file, e.g., `/app/data/images/123.jpg`.
- **`public url`**: `/files/<relative-path-from-DATA_ROOT>`, e.g., `/files/images/123.jpg`.
- Only files under `config.DATA_ROOT` are served; **no** path traversal beyond root.
- Symlinks are either disallowed or must resolve within `config.DATA_ROOT` (reject otherwise).
- Directory browsing is disabled.
- MIME type should match file extension/content (e.g., `image/jpeg`, `image/png`, `image/webp`, `image/gif`).

## 4) API Contract Additions
Where existing endpoints return images (e.g., `GET /images/by-job/{jobId}`), add a field:
```jsonc
{
  "items": [
    {
      "id": "img_001",
      "local_path": "/app/data/images/123.jpg",
      "url": "/files/images/123.jpg",        // NEW
      "width": 1280,
      "height": 720,
      "source": "ebay"
    }
  ]
}
```
- If `local_path` is missing/invalid: `url` must be `null`.
- The API **must not** expose absolute host/container paths in `url`.

## 5) Acceptance Criteria (AC)
### AC‑1 Static Mount Exists
- `GET /files/images/123.jpg` returns **200** and the image bytes when the file exists under `config.DATA_ROOT`.
- When file does not exist: **404**.
- Directory traversal attempts like `/files/../secret` return **403** or **404** (not served).

### AC‑2 Correct URL Derivation
- Given `local_path = config.DATA_ROOT + "/images/a/b/c.jpg"`, returned `url` is `/files/images/a/b/c.jpg`.
- Windows‑style separators are normalized: `\` → `/` in `url`.
- Leading/trailing slashes handled consistently; no duplicate slashes in `url`.

### AC‑3 MIME Types & Headers
- JPEG/PNG/WebP/GIF return correct `Content-Type`.
- Add `Cache-Control: public, max-age=3600` (configurable) for static assets.
- Range requests **may** be supported; if unsupported, downloads still succeed.

### AC‑4 Security
- Static server does **not** allow directory listing.
- Symlinks pointing **outside** of `config.DATA_ROOT` are **not** served.
- CORS allows the known FE origin(s) (e.g., `http://localhost:3000`) for API routes; static files themselves can be public without credentials.
- No absolute internal paths leaked in any JSON body or response headers.

### AC‑5 API Response Integrity
- All list endpoints that include images add the `url` field without changing other fields.
- Backward compatibility: existing consumers relying on `local_path` continue to work.
- `url` is **relative** (begins with `/files/`), so FE can prepend `NEXT_PUBLIC_API_BASE_URL`.

### AC‑6 Front‑End Rendering
- FE composes `<img src={API_BASE + url} />` and images render correctly.
- If `url == null`, FE displays a placeholder image or a “missing image” state.
- FE does not hard‑code the container path or read local files directly.

### AC‑7 Observability
- Application logs include a one‑line info per static request (path, status, duration) in dev.
- Errors (404/5xx) are logged with correlation/request IDs.
- Basic metrics (count of 2xx/4xx/5xx) are emitted or ready to be scraped. (If no metrics stack, keep a counter in logs).

### AC‑8 Performance
- Serving a 1–5 MB image under local dev returns first byte in < 200 ms on typical hardware.
- Concurrent requests (20/sec) do not cause timeouts or memory spikes.
- Streaming is used (no buffering entire file into memory).

## 6) TDD Plan (Tests First)
> Write tests before adding the static mount or URL derivation. Keep tests short and descriptive; no production code in specs.

### 6.1 Backend Unit Tests
1. **`to_public_url` happy path**
   - Input: `local="/app/data/images/1.jpg"`, `DATA_ROOT="/app/data"` → Output: `"/files/images/1.jpg"`.
2. **Windows separators normalized**
   - Input: `local="C:\\data\\images\\x\\y.png"`, `DATA_ROOT="C:\\data"` → Output: `"/files/images/x/y.png"`.
3. **Reject path above root**
   - Input: `local="/app/data/../secret/file.jpg"` → Output: `None` or raise; caller sets `url=null`.
4. **Missing/empty path**
   - Input: `local=None` or `""` → `url=None`.

### 6.2 Backend Integration Tests (with TestClient)
1. **Static 200**
   - Seed a temp file under `DATA_ROOT/images/smoke.jpg`; `GET /files/images/smoke.jpg` → 200 + correct `Content-Type`.
2. **Static 404**
   - `GET /files/images/notfound.jpg` → 404.
3. **Traversal blocked**
   - `GET /files/../etc/passwd` → 403/404.
4. **API contract**
   - `GET /images/by-job/{jobId}` returns each item with `url=/files/...` or `null` when invalid path.
5. **CORS headers (if applicable)**
   - Preflight `OPTIONS` from FE origin returns allowed methods/headers.

### 6.3 Front‑End Tests (Jest + React Testing Library)
1. **Renders with valid URL**
   - Given `item.url="/files/images/1.jpg"` and `NEXT_PUBLIC_API_BASE_URL="http://localhost:8888"`, `<img>` has `src="http://localhost:8888/files/images/1.jpg"`.
2. **Fallback on null URL**
   - `item.url=null` → placeholder rendered (alt text present).
3. **No leakage of `local_path`**
   - Ensure UI never displays `/app/data/...` anywhere.

### 6.4 End‑to‑End (Optional, Playwright)
1. **Happy path**
   - Start stack with a seeded image; navigate to the page; image visible and loaded (HTTP 200).
2. **Missing file**
   - When backend returns `url` to a missing file, UI shows placeholder; network shows 404 handled gracefully.

## 7) Implementation Notes (Non‑Code)
- **Static Mount**: Mount `config.DATA_ROOT` at `/files` using framework’s static file middleware (e.g., FastAPI `StaticFiles`). Disable directory listing.
- **URL Derivation**: Compute `relpath = local_path.relative_to(DATA_ROOT)` (or `os.path.relpath`) → `url = "/files/" + relpath.replace("\\", "/")`. If normalization fails or `..` escapes root, set `url=null`.
- **CORS**: Ensure FE origin(s) allowed for API endpoints. Static files can be public; avoid credentials.
- **Caching**: Add `Cache-Control: public, max-age=3600` for images. Make TTL configurable via env.
- **Error Handling**: 404 for missing files; don’t return 500 for file‑not‑found; log details (not full paths in user‑facing messages).
- **Security**: Reject symlinks escaping root (resolve realpath and verify prefix). No directory listings. Avoid revealing container paths to clients.
- **Observability**: Minimal access log for `/files/*`; tag entries with `request_id`.
- **Compatibility**: Existing consumers using `local_path` remain unaffected; new UIs should use `url`.

## 8) Done Criteria
- All AC in §5 pass.
- All tests in §6 are green in CI.
- Manual verification: open `http://localhost:8888/files/<seeded-image>` in browser and it renders.
- Front‑end renders images with `API_BASE + url` and handles missing images gracefully.

---

### Appendix A — Test Fixtures
- Seed directory: `${DATA_ROOT_HOST}/images/`
- Files:
  - `smoke.jpg` (valid JPEG)
  - `nested/a/b/c.png` (valid PNG)
  - `broken.link` (simulate invalid path mapping)
- Placeholder asset (FE): `/img/placeholder.png`

### Appendix B — Environment
- `DATA_ROOT_HOST` (host path), `DATA_ROOT_CONTAINER` (container path).
- `NEXT_PUBLIC_API_BASE_URL` (FE).

