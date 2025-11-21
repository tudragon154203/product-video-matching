"""
Evidence Phase Test Setup Methods
Contains database setup methods for evidence phase integration tests.
"""
from typing import Dict, Any
import uuid


async def setup_evidence_phase_database_state(
    db_manager,
    job_id: str,
    dataset: Dict[str, Any]
) -> None:
    """Setup database state for evidence phase testing"""

    # Insert video record
    video_record = dataset["video_record"]
    await db_manager.execute(
        """INSERT INTO videos (video_id, platform, url, created_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (video_id) DO NOTHING;""",
        video_record["video_id"], video_record["platform"], video_record["url"]
    )
    await db_manager.execute(
        """INSERT INTO job_videos (job_id, video_id, platform)
           VALUES ($1, $2, $3)
           ON CONFLICT (job_id, video_id) DO NOTHING;""",
        job_id, video_record["video_id"], video_record["platform"]
    )

    # Insert product records
    for product in dataset["products"]:
        await db_manager.execute(
            """INSERT INTO products (product_id, src, asin_or_itemid, marketplace, job_id, created_at)
               VALUES ($1, $2, $3, $4, $5, NOW())
               ON CONFLICT (product_id) DO NOTHING;""",
            product["product_id"], product["src"], product["asin_or_itemid"],
            product["marketplace"], job_id
        )

    # Insert product images
    for img in dataset["product_images"]:
        await db_manager.execute(
            """INSERT INTO product_images (img_id, product_id, local_path, created_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (img_id) DO NOTHING;""",
            img["img_id"], img["product_id"], img["local_path"]
        )

    # Insert video frames
    for frame in dataset["video_frames"]:
        await db_manager.execute(
            """INSERT INTO video_frames (frame_id, video_id, ts, local_path, created_at)
               VALUES ($1, $2, $3, $4, NOW())
               ON CONFLICT (frame_id) DO NOTHING;""",
            frame["frame_id"], frame["video_id"], frame["ts"], frame["local_path"]
        )

    # Insert job record in evidence phase
    await db_manager.execute(
        """INSERT INTO jobs (job_id, phase, industry, created_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (job_id) DO UPDATE SET phase = EXCLUDED.phase;""",
        job_id, "evidence", "test_industry"
    )

    # Insert match records if any
    for match in dataset.get("matches", []):
        match_id = f"{job_id}_{match['product_id']}_{match['video_id']}"
        await db_manager.execute(
            """INSERT INTO matches (
                match_id, job_id, product_id, video_id,
                best_img_id, best_frame_id, ts, score, status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            ON CONFLICT (match_id) DO NOTHING;""",
            match_id, job_id, match["product_id"], match["video_id"],
            match["best_img_id"], match["best_frame_id"],
            match["ts"], match["score"], "accepted"
        )

    # Insert prerequisite phase events
    await db_manager.execute(
        """INSERT INTO phase_events (event_id, job_id, name, received_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (event_id) DO NOTHING;""",
        str(uuid.uuid4()), job_id, "matchings.process.completed"
    )


async def cleanup_evidence_test_database_state(
    db_manager,
    job_id: str
) -> None:
    """Clean up evidence test data"""

    tables_with_job_id = [
        "matches", "phase_events", "jobs"
    ]

    for table in tables_with_job_id:
        try:
            await db_manager.execute(
                f"DELETE FROM {table} WHERE job_id = $1",
                job_id
            )
        except Exception as e:
            print(f"⚠ Could not clean table {table}: {e}")

    # Clean up by ID patterns
    try:
        await db_manager.execute(
            "DELETE FROM products WHERE product_id LIKE $1",
            f"{job_id}%"
        )
    except Exception:
        pass

    try:
        await db_manager.execute(
            "DELETE FROM videos WHERE video_id LIKE $1",
            f"{job_id}%"
        )
    except Exception:
        pass

    try:
        await db_manager.execute(
            "DELETE FROM processed_events WHERE dedup_key LIKE $1",
            f"{job_id}%"
        )
    except Exception:
        pass
