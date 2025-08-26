# SPEC: Collect & Store Products with 2 Parallel Workers (Amazon / eBay)

## 1) Objective

Implement a mechanism with **exactly two parallel workers**: one handling Amazon, one handling eBay. Each worker iterates through the `queries` list sequentially, calls the respective collector to fetch products, then stores them (image + metadata) into storage.

## 2) Scope

- **In scope**: application-level concurrency coordination; calls to `collectors["amazon"|"ebay"].collect_products` and `ImageStorageManager.store_product` with the 2-worker design; logging, local error handling; reporting counts of successfully stored records per platform.
- **Out of scope**: collector crawling logic; storage infrastructure details (S3/NAS/DB); low-level retries already handled by collector/storage manager.

## 3) Functional Requirements (FR)

1. System must spawn **exactly 2 coroutines** in parallel: `amazon_worker` and `ebay_worker`.
2. Each worker:
   - Iterates `queries` in order.
   - For each query, calls its collector to fetch up to `top_k` products.
   - Sequentially calls `store_product(product, job_id, platform)` for each product.
3. At the end, return tuple `(amazon_count, ebay_count)` with number of successfully stored items for each platform.

## 4) Non-Functional Requirements (NFR)

- **Reliability**: a failure in one query/product must **not** crash the entire process (local error handling required).
- **Determinism**: only 2 workers run concurrently; no extra subtasks for storage.
- **Logging**: standardized logging with module `dropship-product-finder`.
- **Monitoring**: log events per query and per product; summarize counters at the end; **special logging to verify concurrency** (record start/finish of each worker to confirm Amazon and eBay execute in parallel).

## 5) Data Flow & Sequence

```
Caller → ProductCollectionManager.collect_and_store_products(job_id, queries, top_amz, top_ebay)
           ├─▶ spawn amazon_worker (async)
           ├─▶ spawn ebay_worker   (async)
           └─▶ await gather(amazon_worker, ebay_worker)

amazon_worker(query...):
  log("Amazon worker START")
  for q in queries:
    products = collectors["amazon"].collect_products(q, top_amz)
    for p in products:
      image_storage_manager.store_product(p, job_id, "amazon")
  log("Amazon worker END")
  return amazon_count

ebay_worker(query...):
  log("Ebay worker START")
  for q in queries:
    products = collectors["ebay"].collect_products(q, top_ebay)
    for p in products:
      image_storage_manager.store_product(p, job_id, "ebay")
  log("Ebay worker END")
  return ebay_count
```

## 6) Concurrency Model

- **Exactly 2 concurrent coroutines** at the top level: `amazon_worker` and `ebay_worker`.
- Inside each worker: **sequential** iteration through `queries` and products, ensuring compliance with the 2-worker constraint.
- No `Semaphore` or nested `gather` for storage subtasks.
- START/END logs confirm workers truly run in parallel.

## 7) Configuration & Parameters

| Parameter  | Type        | Description                          |
| ---------- | ----------- | ------------------------------------ |
| `job_id`   | `str`       | Job identifier for storage reference |
| `queries`  | `List[str]` | List of search keywords              |
| `top_amz`  | `int`       | Max products per query for Amazon    |
| `top_ebay` | `int`       | Max products per query for eBay      |

## 8) Interfaces & Constraints

- `collectors: Dict[str, IProductCollector]` must contain keys `"amazon"`, `"ebay"`.
- `IProductCollector.collect_products(query: str, top_k: int) -> List[dict]` (async).
- `ImageStorageManager.store_product(product: dict, job_id: str, platform: str) -> Awaitable[None]`.
- `product` must at least include `id` or `sku` for logging when errors occur.

## 9) Logging & Error Handling

- **Collector errors**: log `logger.exception("[platform] Collect failed for query='{q}': {e}")`, continue with next query.
- **Storage errors**: log `logger.exception("[platform] Store failed (id={pid}) for query='{q}': {e}")`, skip that product.
- **Worker lifecycle**: log `logger.info("[platform] Worker START job={job_id}")` at start, `logger.info("[platform] Worker END job={job_id}, count={count}")` at end to confirm concurrency.
- **Summary**: log total `amazon_count`, `ebay_count` after `gather`.

## 10) Safety & Rate-limiting

- Only 2 concurrent workers, so rate-limit risk is low. If stricter platform rules:
  - Add `asyncio.sleep(backoff)` in collector (outside this spec), or
  - Add light throttling between queries within worker, but still keeping exactly 2 workers.

## 11) Success Metrics (KPIs)

- Success rate = (amazon\_count + ebay\_count) / total returned products.
- Job completion time (from `collect_and_store_products` start to finish).
- Error counts by type (collect/store) and platform.
- Log evidence of concurrency: START/END logs from both workers must overlap.

## 12) Testing Plan

1. **Happy path**: 2–3 `queries`, each collector returns ≤ `top_k`, all stored OK → check counts & logs.
2. **Collector failure on one query**: mock raises exception → process continues, counts skip failed query, logs exception.
3. **Storage failure on one product**: mock raises exception → counts not incremented, logs product id/sku.
4. **Edge cases**: `queries=[]` → returns `(0,0)`; `top_k=0` → collectors return empty, no storage calls.
5. **Concurrency check**: assert Amazon and eBay START logs are close in time and END logs overlap.

## 13) Limitations & Assumptions

- Performance depends on collector; within each worker, throughput ≈ O(len(queries) \* top\_k).
- `store_product` is I/O-bound but runs sequentially to comply with 2-worker constraint.

## 14) Reference Pseudocode

```python
async def collect_and_store_products(job_id, queries, top_amz, top_ebay):
    async def _process(platform: str, top_k: int) -> int:
        count = 0
        logger.info(f"[{platform}] Worker START job={job_id}")
        for q in queries:
            try:
                products = await collectors[platform].collect_products(q, top_k)
            except Exception as e:
                log_collect_error(platform, q, e)
                continue
            for p in products:
                try:
                    await image_storage_manager.store_product(p, job_id, platform)
                    count += 1
                except Exception as e:
                    log_store_error(platform, q, p, e)
        logger.info(f"[{platform}] Worker END job={job_id}, count={count}")
        return count

    amz_task = asyncio.create_task(_process("amazon", top_amz))
    eby_task = asyncio.create_task(_process("ebay",   top_ebay))
    return await asyncio.gather(amz_task, eby_task)
```

## 15) Future Enhancements (optional)

- Add **parallel storage window** with Semaphore, while still maintaining 2 top-level workers.
- Provide **detailed counters** per query and per status.
- Integrate **tracing** (OpenTelemetry) to measure time for collect/store stages.

