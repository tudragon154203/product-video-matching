# Matcher Microservice

The matcher service ranks and verifies product–video pairs once upstream
services have produced embeddings and keypoints. It pulls stored features from
Postgres, runs vector similarity search to shortlist candidate frames, applies
lightweight pair scoring, and emits contract-compliant events for downstream
consumers.

## High-level flow
1. Consume `match.request` events containing `{ job_id, event_id }`.
2. Load product images and video frames for the job from Postgres, including
   `emb_rgb`, `emb_gray`, and `kp_blob_path` populated by vision services.
3. For each product image, run `VectorSearcher` to retrieve the top-K most
   similar frames (pgvector-style query with numpy fallback).
4. Score each candidate pair with `PairScoreCalculator`, mixing embedding and
   keypoint signals.
5. Aggregate matches via `MatchAggregator`, apply acceptance thresholds, and
   publish `match.result` events plus a terminal
   `match.request.completed` event (always emitted once per job, even when no
   pairs are accepted, to unblock the evidence builder).

## Code structure
- `matching/` – `MatchingEngine`, the orchestration layer around search,
  scoring, and aggregation.
- `matching_components/` – vector search, pair scoring, and aggregation helper
  classes.
- `services/service.py` – orchestrates job-level processing, persists matches,
  and publishes events.
- `handlers/matcher_handler.py` – wires up database/broker connections and
  validates incoming events.
- `embedding_similarity.py` – cosine similarity helpers for RGB/gray vectors.
- `config_loader.py` – loads global + service-specific configuration.

## Configuration
Environment variables are loaded from `.env` in conjunction with the shared
`libs/config`. Key values:

| Variable | Description |
| --- | --- |
| `POSTGRES_*`, `BUS_BROKER`, `DATA_ROOT_CONTAINER` | Supplied by global config |
| `RETRIEVAL_TOPK` | Number of candidate frames to consider (default 20) |
| `SIM_DEEP_MIN` | Minimum embedding similarity for acceptance (default 0.82) |
| `INLIERS_MIN` | Minimum keypoint inlier ratio (default 0.35) |
| `MATCH_BEST_MIN`, `MATCH_CONS_MIN`, `MATCH_ACCEPT` | Aggregation thresholds |

## Development
Install dependencies and run unit tests from the service directory:

```bash
pip install -r requirements.txt
python -m pytest tests/unit -v
```

A local Postgres instance populated with embeddings/keypoints is required for
full integration testing; unit tests rely on mocks for database and broker
interactions.
