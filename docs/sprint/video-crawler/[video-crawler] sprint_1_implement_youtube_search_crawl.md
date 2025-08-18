# YouTube Crawler Spec — `services/video-crawler/platform_crawler/youtube_crawler.py`

## Goal
Implement `YoutubeCrawler` (search + download only) for keyword-based YouTube retrieval using **yt-dlp**, saving files under `{VIDEO_DIR}/youtube`.

## Scope
- ✅ **Supported now:** keyword **search (relevance-first)** → **download** → return normalized results.
- ❌ **Not supported now:** channel URLs, playlist URLs, any direct URL inputs (skip with log).

## Interface Compliance
- Class: `class YoutubeCrawler(PlatformCrawlerInterface):`
- Method signature (must be `async`):
  ```python
  async def search_and_download_videos(
      self, queries: List[str], recency_days: int, download_dir: str
  ) -> List[Dict[str, Any]]
  ```
- Each returned dict must include:
  - `platform` = `"youtube"`
  - `video_id`
  - `url` (canonical watch URL)
  - `title`
  - `duration_s` (int or None)
  - `published_at` (ISO 8601 or `YYYY-MM-DD` in UTC)
  - `local_path` (absolute path to downloaded file)

## Configuration
Add **`VIDEO_DIR`** to service config and use it for all YouTube downloads.

- Create **`services/video-crawler/.env.example`**:
  ```
  # Root directory where downloaded videos are stored
  VIDEO_DIR=/absolute/path/to/videos
  ```
- Create **`services/video-crawler/.env`** (developer-specific):
  ```
  VIDEO_DIR=/abs/path/on/this/machine/videos
  ```
- The caller must set:
  ```
  download_dir = os.path.join(config.VIDEO_DIR, "youtube")
  ```
- **Max results** comes from the **incoming event** (not config). Enforce that per query.

## Download Location Rule
All files must be saved strictly under:
```
{VIDEO_DIR}/youtube/<uploader>/<title>.<ext>
```
Create directories as needed; sanitize filenames.

## Operational Flow
1) **Search (relevance-first)**
   - For each keyword `query`, use `ytsearch{N}:{query}` where `N` is provided by the event.
   - Flat extract metadata (no download); parse `upload_date` → `published_at`.
   - Apply `recency_days` filter: `published_at >= now - recency_days`.
   - Deduplicate by `video_id` across all queries.
   - Enforce per-query `N` from the event.

2) **Download**
   - Download selected items to `{VIDEO_DIR}/youtube/...`.
   - If target file already exists, skip download and reuse it.
   - Collect final absolute `local_path`.

3) **Return**
   - Return only items that successfully produced (or reused) a file, each with the required fields.

## Input / Output
**Input**  
- `queries`: List[str] **(keywords only; URLs ignored)**  
- `recency_days`: int (UTC-based lookback)  
- `download_dir`: must be `{VIDEO_DIR}/youtube` (from config)

**Output**  
- `List[Dict[str, Any]]` with required keys per video (see Interface Compliance)

## Error Handling & Logs
- Per-item isolation: failures don’t abort others.
- Log reasons for skips (URL input, duplicate, too old, download failure).
- If all fail, return `[]`.

## Acceptance Criteria
- Implements the exact async interface.
- Uses **relevance** (not newest) for search.
- Only keyword searches are processed; URL-like inputs are skipped with a log.
- Files saved strictly under `{VIDEO_DIR}/youtube/...`.
- Event-provided `max results` and `recency_days` are enforced.
- Each result includes `platform, video_id, url, title, duration_s, published_at, local_path`.
- Per-item failures do not block others.
- `.env` and `.env.example` exist with `VIDEO_DIR`.

## TODO (install early)
- [ ] **Add `yt-dlp` to `services/video-crawler/requirements.txt` and install** (`pip install -r services/video-crawler/requirements.txt`).
- [ ] Add `VIDEO_DIR` to service config; create `.env` and `.env.example` as above.
- [ ] Implement `YoutubeCrawler.search_and_download_videos(...)` (exact signature).
- [ ] Search via `ytsearch{N}:{query}` (relevance), apply `recency_days` filter, dedup by `video_id`, enforce per-query `N` from event.
- [ ] Download into `{VIDEO_DIR}/youtube/...` with safe filenames; reuse file if it exists.
- [ ] Return normalized dicts with all required fields.
- [ ] Tests: recency filter, dedup across queries, save path under `VIDEO_DIR/youtube`, URL-input skip, per-item failure isolation.
