# Main API Spec — Single `query` + Ollama (Updated per requests)
**Version:** 0.3  
**Changes:** (1) Bỏ security; (2) Đặt `.env` phụ riêng cho service **main-api**; (3) Pseudocode **không dùng `os.getenv()`**; (4) `OLLAMA_TIMEOUT_S = 60`.

---

## 1) Tóm tắt
- Client gửi **1 trường** `query`.
- Main API gọi **Ollama** để: (A) phân loại `industry` (zero-shot), (B) sinh `queries` đa ngôn ngữ (product.en / video.vi / video.zh).
- Lưu vào `jobs` và publish 2 events: `products.collect.request`, `videos.search.request`.
- **Không** yêu cầu bảo mật (API key) trong phạm vi spec này.

---

## 2) API Surface (Main API)

### 2.1 `POST /start-job`
**Request**
```json
{ "query": "string", "top_amz": 20, "top_ebay": 20, "platforms": ["youtube","bilibili"], "recency_days": 30 }
```
**Response (202)**
```json
{ "job_id": "uuid", "status": "started" }
```
**Flow**
1) Tạo `job_id`.  
2) Gọi Ollama **classify** → `industry` (1 label).  
3) Gọi Ollama **generate** → `queries` (JSON schema cố định).  
4) Ghi DB: `jobs(job_id, query, industry, queries, phase='collection', created_at, updated_at)`.  
5) Publish events:
   - `products.collect.request` → `{job_id, industry, top_amz, top_ebay}`
   - `videos.search.request` → `{job_id, industry, queries(video.*), platforms, recency_days}`

### 2.2 `GET /status/{job_id}`
Trả `phase`, `percent`, `counts` như trước.

### 2.3 `GET /health`
Kiểm tra DB, broker và **Ollama** (ví dụ gọi `/api/tags`).

---

## 3) DB Schema
```sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS query   TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS queries  JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS phase    TEXT DEFAULT 'collection';
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);
```

---

## 4) Cấu hình `.env` **riêng cho service main-api**
Đặt file: `services/main-api/.env` (hoặc `.env.local` cho dev)

```
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_CLASSIFY=qwen3:4b-instruct
OLLAMA_MODEL_GENERATE=qwen3:4b-instruct
OLLAMA_TIMEOUT_S=60

# Labels (dạng CSV)
INDUSTRY_LABELS=fashion,beauty_personal_care,books,electronics,home_garden,sports_outdoors,baby_products,pet_supplies,toys_games,automotive,office_products,business_industrial,collectibles_art,jewelry_watches,other

# Defaults (nếu client không truyền)
DEFAULT_TOP_AMZ=20
DEFAULT_TOP_EBAY=20
DEFAULT_PLATFORMS=youtube,bilibili
DEFAULT_RECENCY_DAYS=30
```

> **Quan trọng**: Service **main-api** tự load **file env cục bộ của chính nó** (không dùng env global).

---

## 5) Prompts (giữ nguyên cấu trúc)
### 5.1 Classify (zero-shot, output 1 nhãn)
```
Bạn là bộ phân loại zero-shot. 
Nhiệm vụ: Gán truy vấn sau vào đúng 1 nhãn industry trong danh sách cho trước.

YÊU CẦU BẮT BUỘC:
- Chỉ in ra đúng 1 nhãn duy nhất, không thêm chữ nào khác.
- Nếu độ chắc chắn thấp, hãy chọn "other".
- Danh sách nhãn hợp lệ: [{INDUSTRY_LABELS_CSV}]

Truy vấn:
{QUERY}
```

### 5.2 Generate queries (JSON-only)
Schema kỳ vọng:
```json
{ "product": { "en": ["..."] }, "video": { "vi": ["..."], "zh": ["..."] } }
```
Prompt (đã bỏ phần “theo industry” đặc thù):
```
Bạn là bộ sinh từ khoá tìm kiếm đa ngôn ngữ cho TMĐT và video.

ĐẦU VÀO:
- query_goc = "{QUERY}"
- industry = "{INDUSTRY}"

YÊU CẦU ĐẦU RA:
- Chỉ in RA JSON hợp lệ theo schema:
  {
    "product": { "en": [strings...] },
    "video":   { "vi": [strings...], "zh": [strings...] }
  }

QUY TẮC:
1) "product.en": 2–4 cụm từ tiếng Anh để tìm sản phẩm/dropship.
2) "video.vi": 2–4 cụm từ tiếng Việt để tìm video.
3) "video.zh": 2–4 cụm từ tiếng Trung giản thể để tìm video.
4) Không vượt quá 5 từ khoá mỗi nhóm; không thêm chú thích ngoài JSON.
5) Giữ nghĩa cốt lõi của query_goc; không bịa thương hiệu.

BẮT ĐẦU.
```

---

## 6) Pseudocode (không dùng `os.getenv()`)
Sử dụng **Config object** nạp từ file `.env` của chính service (ví dụ `load_env(path)` → dict → dataclass).

```python
# config_loader.py (ví dụ)
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MainAPIConfig:
    ollama_host: str
    model_classify: str
    model_generate: str
    ollama_timeout_s: int
    industry_labels: list[str]
    default_top_amz: int
    default_top_ebay: int
    default_platforms: list[str]
    default_recency_days: int

def load_env(env_path: str) -> MainAPIConfig:
    # đọc file .env riêng (services/main-api/.env), parse thủ công hoặc dùng dotenv
    kv = parse_env_file(env_path)  # bạn tự hiện thực parse_env_file()
    return MainAPIConfig(
        ollama_host=kv["OLLAMA_HOST"],
        model_classify=kv["OLLAMA_MODEL_CLASSIFY"],
        model_generate=kv["OLLAMA_MODEL_GENERATE"],
        ollama_timeout_s=int(kv.get("OLLAMA_TIMEOUT_S", 60)),
        industry_labels=[x.strip() for x in kv["INDUSTRY_LABELS"].split(",")],
        default_top_amz=int(kv.get("DEFAULT_TOP_AMZ", 20)),
        default_top_ebay=int(kv.get("DEFAULT_TOP_EBAY", 20)),
        default_platforms=[x.strip() for x in kv.get("DEFAULT_PLATFORMS","youtube,bilibili").split(",")],
        default_recency_days=int(kv.get("DEFAULT_RECENCY_DAYS", 30)),
    )
```

```python
# start_job.py (ví dụ rút gọn)
import json, time, ollama
from uuid import uuid4

def start_job(payload: dict, cfg: MainAPIConfig, db, broker):
    job_id = str(uuid4())
    q = payload["query"].strip()

    # A) classify
    cls_prompt = build_cls_prompt(q, cfg.industry_labels)
    t0 = time.time()
    try:
        res = ollama.generate(
            model=cfg.model_classify,
            prompt=cls_prompt,
            options={"timeout": cfg.ollama_timeout_s*1000}  # ms
        )
        industry = res["response"].strip()
        if industry not in cfg.industry_labels:
            industry = "other"
    finally:
        log_ms("ollama_classify_ms", (time.time()-t0)*1000)

    # B) generate queries
    gen_prompt = build_gen_prompt(q, industry)
    t0 = time.time()
    try:
        res = ollama.generate(
            model=cfg.model_generate,
            prompt=gen_prompt,
            options={"temperature": 0.2, "timeout": cfg.ollama_timeout_s*1000}
        )
        queries = json.loads(res["response"])
        queries = normalize_queries(queries, min_items=2, max_items=4)
    except Exception:
        queries = {"product":{"en":[q]}, "video":{"vi":[q], "zh":[q]}}
    finally:
        log_ms("ollama_generate_ms", (time.time()-t0)*1000)

    # C) persist & publish
    db.insert_job(job_id, q, industry, queries, phase="collection")
    broker.publish("products.collect.request", {
        "job_id": job_id, "industry": industry,
        "top_amz": payload.get("top_amz", cfg.default_top_amz),
        "top_ebay": payload.get("top_ebay", cfg.default_top_ebay),
    })
    video_queries = route_video_queries(queries, payload.get("platforms", cfg.default_platforms))
    broker.publish("videos.search.request", {
        "job_id": job_id, "industry": industry,
        "queries": video_queries,
        "platforms": payload.get("platforms", cfg.default_platforms),
        "recency_days": payload.get("recency_days", cfg.default_recency_days),
    })
    return {"job_id": job_id, "status": "started"}
```

> Ghi chú:
> - `ollama` Python lib đọc `OLLAMA_HOST` từ environment hệ thống. Nếu bạn muốn **tuyệt đối** không dùng env, hãy cấu hình host khi khởi tạo client hoặc set ở tầng networking (proxy). Trong đa số trường hợp, chỉ cần export `OLLAMA_HOST` trong `.env` của service là đủ.

---

## 7) Acceptance Tests (không đổi)
- `POST /start-job` → `202` + `job_id`
- DB có `query`, `industry in labels`, `queries` đúng schema JSON
- Publish 2 events đúng schema
- `/status/{job_id}` hoạt động
- `/health` OK khi Ollama chạy

