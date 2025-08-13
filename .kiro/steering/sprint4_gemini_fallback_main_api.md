# Sprint 4 — Fallback Gemini cho main-api

## 🌟 Mục tiêu

1. Bổ sung biến môi trường cho **Gemini** vào `.env` của `services/main-api`:
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL`
2. Đổi tên biến `OLLAMA_TIMEOUT` thành `LLM_TIMEOUT` (dùng chung cho cả Ollama và Gemini).
3. Triển khai **fallback**: nếu Ollama bị timeout hoặc lỗi, tự động chuyển sang gọi Gemini.

---

## 🧬 Phạm vi & Deliverables

- Cập nhật **services/main-api/.env.example** (và `.env` nếu có) với `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_TIMEOUT`.
- Cập nhật **config\_loader** để đọc các biến mới.
- Thêm **client Gemini** đơn giản (HTTP) + hàm `call_gemini()`.
- Bổ sung \*\*hàm wrapper \*\*\`\`: thử Ollama trước, nếu lỗi/timeout → fallback sang Gemini.
- Cập nhật luồng gọi model trong `main-api` sang dùng `call_llm()`.
- Bổ sung test cho fallback (mock timeout Ollama, kỳ vọng gọi Gemini).

---

## 🛠️ Thiết kế ngắn gọn

### 1) Biến môi trường

**services/main-api/.env.example**:

```env
# Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# LLM Timeout (seconds)
LLM_TIMEOUT=60
```

### 2) Đọc cấu hình

**config\_loader.py**:

```python
@dataclass
class MainAPIConfig:
    # Ollama
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    OLLAMA_MODEL_CLASSIFY: str = os.getenv("OLLAMA_MODEL_CLASSIFY", "qwen3:4b-instruct")
    OLLAMA_MODEL_GENERATE: str = os.getenv("OLLAMA_MODEL_GENERATE", "qwen3:4b-instruct")

    # LLM chung
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
```

### 3) Lớp gọi LLM

**main.py**:

```python
async def call_gemini(model: str, prompt: str, timeout_s: int, **kwargs) -> dict:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    headers = {"Authorization": f"Bearer {config.GEMINI_API_KEY}"}
    payload = {"model": model, "input": prompt}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.post("https://generativelanguage.googleapis.com/v1beta/models:generateContent",
                              headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"response": text}

async def call_llm(kind: str, prompt: str, **kwargs) -> dict:
    timeout_s = config.LLM_TIMEOUT
    model = config.OLLAMA_MODEL_CLASSIFY if kind == "classify" else config.OLLAMA_MODEL_GENERATE
    try:
        return await call_ollama(model=model, prompt=prompt, timeout_s=timeout_s, **kwargs)
    except (asyncio.TimeoutError, httpx.HTTPError, Exception) as e:
        print({"phase": "llm_call", "provider": "ollama", "status": "error", "fallback": "gemini", "reason": str(e)})
        return await call_gemini(model=config.GEMINI_MODEL, prompt=prompt, timeout_s=timeout_s, **kwargs)
```

### 4) Tích hợp

- Thay gọi `call_ollama()` trong runtime bằng `call_llm()`.
- Giữ nguyên `call_ollama()` để không phá test cũ.

---

## ✅ Tiêu chí chấp nhận

1. `services/main-api/.env.example` có `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_TIMEOUT`.
2. `config_loader` đọc được biến mới, API key rỗng không gây crash.
3. Ollama timeout/lỗi → fallback Gemini hoạt động, log lý do.
4. Cả hai lỗi → trả 5xx, tiếp tục chạy.
5. Test cũ pass, test mới fallback pass.

---

## 📚 Kế hoạch triển khai

1. **Cấu hình**:
   - Thêm `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_TIMEOUT` vào `.env.example`.
   - Cập nhật file `.env` thực tế khi triển khai.
2. **Code**:
   - Sửa `config_loader.py` thêm biến mới.
   - Viết hàm `call_gemini()` và `call_llm()` trong `main.py`.
   - Sửa các điểm gọi model để dùng `call_llm()`.
3. **Test**:
   - Viết test mock timeout Ollama → fallback Gemini.
   - Đảm bảo test cũ không bị ảnh hưởng.
4. **Triển khai**:
   - Build lại `main-api` bằng Docker Compose.
   - Khởi động lại dịch vụ.
5. **Giám sát**:
   - Theo dõi log để xác nhận fallback hoạt động.

---

## 🚀 Rollout 

```bash
docker compose -f infra/pvm/docker-compose.dev.yml build main-api
docker compose -f infra/pvm/docker-compose.dev.yml up -d main-api
```



