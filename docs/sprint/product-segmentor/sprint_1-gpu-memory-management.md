# GPU Memory Management for Product Segmentor

The product-segmentor worker intermittently runs out of GPU memory, which ruins segmentation batches and causes downstream jobs to stall. This document lays out the problem, the measurable impact, and the plan to stabilize memory usage without losing throughput.

## Problem Statement

During high-volume processing the service raises CUDA out-of-memory (OOM) and cuDNN allocation errors. Failed frames must be retried later, which inflates job duration and reduces the number of usable masks per batch.

### Observed Symptoms

- Repeated `CUDA out of memory. Tried to allocate <X> MiB` exceptions (12MB–192MB observed)
- `cuDNN error: CUDNN_STATUS_ALLOC_FAILED` surfaced during both RMBG and YOLO runs
- Segmentation failure rate spikes to ~15–30% whenever multiple jobs overlap
- Foreground and people masks drop simultaneously, implying shared bottlenecks
- Failures arrive in bursts, suggesting fragmentation rather than single huge frames

### Root Cause Analysis

**What the code currently does**

- `ProductSegmentorService` initializes RMBG and YOLO models once at startup and holds on to them for the lifetime of the worker (`services/product-segmentor/services/service.py:66`).
- Concurrency is capped only for `products.image.ready` events via an `asyncio.Semaphore` constructed from `MAX_CONCURRENT_IMAGES` (`services/.../service.py:115`). Video frame batches bypass this semaphore and iterate frame-by-frame, so multiple video jobs can still execute in parallel without any GPU gating.
- `ImageMaskingProcessor` runs RMBG and YOLO sequentially for every asset, meaning both models must co-reside in VRAM for the duration of a frame (`services/.../services/image_masking_processor.py:16`).
- `RMBG20Segmentor` uses CUDA tensors but only calls `torch.cuda.empty_cache()` in its `cleanup` method, which is reached during service shutdown, not mid-run (`services/.../segmentation/models/rmbg20_segmentor.py:116`).
- YOLO segmentation happens through `ultralytics.YOLO.predict`, which internally keeps CUDA buffers around and has no explicit cleanup hooks (`services/.../segmentation/models/yolo_segmentor.py:66`).
- No module logs `torch.cuda.mem_get_info()` or any GPU utilization metrics, so operators have no observability into allocator pressure.

**Memory accumulation pattern**

1. Baseline model footprint: ≈3 GB (RMBG + YOLO)
2. Per-frame work buffers: 150–250 MB per concurrent task at 512×512
3. Two concurrent frames push total to ~3.5–4.0 GB before fragmentation
4. Additional 500 MB–1 GB of transient tensors linger because no cleanup occurs
5. After several batches the allocator fragments memory, forcing OOM on even small allocations

## Impact

- ~15–30% of frames fail under load, directly reducing segmentation coverage
- Jobs spend extra minutes replaying dropped frames, dragging out end-to-end completion time
- Missing masks block downstream embedding/keypoint extraction and reduce final match confidence
- OOM events contaminate logs and hide other operational alerts

## Goals

1. Keep CUDA OOM rates below 1% in steady state (<5% during mitigation)
2. Preserve throughput so that an optimized GPU still operates near baseline utilization
3. Provide graceful degradation (retry with cleanup) when memory pressure spikes
4. Produce predictable resource requirements that inform capacity planning

## Solution Options

### Solution 1: Adaptive Concurrency with GPU Memory Monitoring

Let GPU memory availability, not a static semaphore, dictate how many frames can process simultaneously.

**Approach**

- Add a `GPUMemoryMonitor` that samples `torch.cuda.mem_get_info()` before `ImageMaskingProcessor.process_single_image` is invoked.
- Replace the plain `asyncio.Semaphore` in `ProductSegmentorService` with a memory-aware wrapper that can block `handle_products_image_ready` and `handle_videos_keyframes_ready` alike so video batches stop ignoring GPU pressure.
- Trigger periodic cleanup (`torch.cuda.empty_cache()` + `torch.cuda.synchronize()`) every _N_ frames from within the monitor to reclaim fragmented blocks.
- Emit structured logs/metrics for used vs. available GPU memory and expose them via the existing logging stack.

**Benefits**

- Self-tunes as frame sizes, GPU tiers, or model footprints change
- Prevents OOM events proactively rather than reacting after a crash
- Requires no manual per-environment tuning beyond thresholds

**Trade-offs**

- Adds roughly 10–20 ms of bookkeeping per frame
- Slightly more complex control flow (memory monitor + adaptive semaphore)

**Key configuration**

```bash
GPU_MEMORY_THRESHOLD=0.85   # Begin blocking new tasks at 85% usage
MIN_CONCURRENT_IMAGES=1     # Never drop below one worker unless GPU unavailable
MAX_CONCURRENT_IMAGES=4     # Existing upper cap; tuned per GPU tier
```

### Solution 2: Targeted Retry with Forced Cleanup (Former “Solution 5”)

Catch OOM exceptions, clear caches, and retry the failed frame with exponential backoff so transient spikes do not permanently drop work.

**Approach**

- Wrap `AssetProcessor.handle_single_asset_processing` with try/except for CUDA OOM strings so both product images and video frames get the same recovery behavior.
- On failure, call `torch.cuda.empty_cache()` and `torch.cuda.synchronize()`, wait (0.5 s → 1 s → 2 s), and retry up to `MAX_OOM_RETRIES`
- Emit structured logs showing retry attempts and final disposition

**Benefits**

- Recovers from momentary spikes or fragmentation without discarding the frame
- Low-code change (~50 lines) and deployable immediately
- Plays nicely with Solution 1; retries should be rare once adaptive control ships

**Trade-offs**

- Adds latency (3–7 s) when a frame needs all retries
- Does not eliminate the root cause—it only softens the failure mode

**Key configuration**

```bash
RETRY_ON_OOM=true
MAX_OOM_RETRIES=3
```

## Recommended Implementation Plan

### Phase 1 – Immediate Mitigation (Week 1)

Goal: cut OOM rate to <5% while we build adaptive control.

1. Implement Solution 2
   - Add OOM-aware retry wrapper in `asset_processor.py`
   - Introduce configuration flags and default retries
   - Add unit tests mocking CUDA errors to confirm cleanup + retries
2. Temporarily set `MAX_CONCURRENT_IMAGES=1` in `.env` and `.env.example`
3. Instrument logs with GPU memory usage (start/end of each batch)

Deliverables: retry logic deployed, memory logs available, and measured OOM rate <5%.

### Phase 2 – Adaptive Concurrency (Weeks 2–3)

Goal: proactive memory management with throughput near baseline.

1. Implement Solution 1
   - Create `GPUMemoryMonitor` and integrate with the service semaphore
   - Add configurable cleanup cadence
   - Wire up Prometheus metrics for memory usage, throttling counts, and concurrency levels
2. Test on 8 GB, 16 GB, and 24 GB GPUs to tune thresholds
3. Restore `MAX_CONCURRENT_IMAGES` to GPU-specific optimal values (documented in runbook)

Deliverables: adaptive control in production, zero OOMs under nominal load, and <10% throughput regression.

### Phase 3 – Production Hardening (Week 4)

Goal: operational guardrails and documentation.

1. Roll out dashboards + alerts (see Monitoring section)
2. Document capacity planning, tuning guidance, and an OOM incident runbook
3. Execute load tests (1,000+ frames, multi-job scenarios, 24-hour soak)

Deliverables: dashboards online, docs published, and load tests passing.

## Success Metrics

- **CUDA OOM rate**: <1% steady state (starting from ~15–30%)
- **Frame success rate**: >99% processed without manual intervention
- **Average per-frame latency**: within ±10% of current baseline
- **GPU utilization**: maintain 70–85% to avoid both starvation and OOMs
- **P95 latency**: <5 s per frame after mitigation

## Monitoring & Alerting

**Expose**

- `gpu_memory_used_bytes` / `gpu_memory_available_bytes`
- `segmentation_oom_errors_total`
- `segmentation_retry_attempts_total`
- `segmentation_processing_duration_seconds` (histogram)
- `concurrent_segmentation_tasks`

**Alert when**

- OOM rate >5% over 5 minutes
- GPU utilization >95% for >2 minutes
- Frame success rate <95%
- Average processing time doubles relative to baseline

## Configuration Reference

**Current variables**

```bash
# Models
FOREGROUND_SEG_MODEL_NAME=briaai/RMBG-2.0
PEOPLE_SEG_MODEL_NAME=yolo11l-seg
HF_TOKEN=hf_xxx

# Processing
MAX_CONCURRENT_IMAGES=2
BATCH_TIMEOUT_SECONDS=1800
MASK_QUALITY=0.8

# Output paths
FOREGROUND_MASK_REL_PATH=./masks_foreground
PEOPLE_MASK_REL_PATH=./masks_people
PRODUCT_MASK_REL_PATH=./masks_product

LOG_LEVEL=INFO
```

**New variables**

```bash
# Adaptive concurrency
GPU_MEMORY_THRESHOLD=0.85
MIN_CONCURRENT_IMAGES=1

# Retry logic
RETRY_ON_OOM=true
MAX_OOM_RETRIES=3
```

## Code Touchpoints

- `services/product-segmentor/config_loader.py`: add new settings
- `services/product-segmentor/services/service.py`: wire in the memory monitor, replace `_processing_semaphore`, and ensure `handle_videos_keyframes_ready` respects the same gate
- `services/product-segmentor/services/asset_processor.py`: implement retry logic
- `services/product-segmentor/segmentation/models/rmbg20_segmentor.py` and `.../yolo_segmentor.py`: ensure periodic cache clearing hooks
- `services/product-segmentor/.env.example`: document new knobs

## Testing Strategy

- **Unit**: simulate OOM exceptions to verify retry/backoff, ensure memory monitor thresholds gate concurrency correctly, and test cleanup helpers
- **Integration**: process 100+ frames, mix HD/FHD inputs, and force low-memory conditions
- **Load**: soak tests with multi-job concurrency and 1,000-frame batches

Acceptance criteria: zero OOMs in a 1,000-frame test, predictable latency under varying batch sizes, and graceful recovery from forced OOM injections.

## Rollout Plan

1. **Development**: land Phase 1 fixes, run unit/integration tests locally
2. **Staging**: deploy with monitoring enabled, execute load tests, tune thresholds
3. **Production Canary**: enable for 10% of traffic for 48 hours while watching metrics
4. **Full Production**: ramp to 100% with continued monitoring and retrospective write-up

## Rollback Plan

If OOMs spike or throughput collapses:

1. Immediately set `MAX_CONCURRENT_IMAGES=1`
2. Disable retries via `RETRY_ON_OOM=false` (to avoid masking regressions)
3. Disable adaptive gating by setting `GPU_MEMORY_THRESHOLD=1.0`
4. Scale horizontally (additional service replicas with dedicated GPUs)

## Future Considerations

- Multi-GPU sharding to divide workloads per device
- CPU fallback path for emergency processing when GPUs are unavailable
- Investigate lighter-weight segmentation models or quantization to shrink base footprint
- Streaming ingestion so frames are processed progressively instead of in large bursts
- Model lifecycle hooks that unload rarely used models to release memory

## References

- PyTorch CUDA memory notes: https://pytorch.org/docs/stable/notes/cuda.html
- NVIDIA CUDA best practices: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/
- Product Segmentor source: `services/product-segmentor/`
- Related incident: GPU OOM during high-volume processing

## Appendix: Memory Profiling Snapshot

- RMBG-2.0 load: ~2 GB
- YOLO11l-seg load: ~1 GB
- Per-frame (512×512) buffers: 150–250 MB
- Intermediate tensors: 100–200 MB per frame
- Additional allocator overhead: ~500 MB
- Total baseline (2 concurrent frames): ≈3.5–4 GB

**Estimated safe concurrency by GPU size**

- 8 GB: 1–2 frames
- 16 GB: 3–4 frames
- 24 GB: 6–8 frames
- 32 GB+: 8–10 frames

**Leak indicators**

- Gradual memory increase across batches
- OOM errors appearing only late in a job
- Allocation requests that grow from 12 MB to 192 MB over time

**Outstanding gaps addressed above**

1. No mid-run `torch.cuda.empty_cache()` calls
2. Models stay pinned in memory indefinitely
3. No monitoring or adaptive throttling
4. Cleanup only at service shutdown
5. No retry logic around transient OOMs
6. Semaphore enforces concurrency count, not memory availability
