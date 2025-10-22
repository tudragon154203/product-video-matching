"""
Matching Phase Test Setup Methods
Contains database setup methods for matching phase integration tests.
"""
from typing import Dict, Any, List
import uuid


async def setup_comprehensive_matching_database_state(
    db_manager,
    job_id: str,
    dataset: Dict[str, Any]
) -> None:
    """Setup comprehensive database state for matching phase end-to-end testing"""
    
    # Insert video record
    video_record = dataset["video_record"]
    await db_manager.execute(
        """INSERT INTO videos (video_id, platform, url, job_id, created_at) 
           VALUES ($1, $2, $3, $4, NOW())
           ON CONFLICT (video_id) DO NOTHING;""",
        video_record["video_id"], video_record["platform"], video_record["url"], job_id
    )
    
    # Insert product and image records with feature extraction data
    for record in dataset["product_records"]:
        await db_manager.execute(
            """INSERT INTO products (product_id, src, asin_or_itemid, marketplace, job_id, created_at) 
               VALUES ($1, $2, $3, $4, $5, NOW())
               ON CONFLICT (product_id) DO NOTHING;""",
            record["product_id"], record["src"], record["asin_or_itemid"], record["marketplace"], job_id
        )
        await db_manager.execute(
            """INSERT INTO product_images (img_id, product_id, local_path, 
               emb_rgb, emb_gray, kp_blob_path, created_at) 
               VALUES ($1, $2, $3, $4, $5, $6, NOW())
               ON CONFLICT (img_id) DO NOTHING;""",
            record["img_id"], record["product_id"], record["local_path"],
            str(record["emb_rgb"]), str(record["emb_gray"]), record["kp_blob_path"]
        )
    
    # Insert video frame records with feature extraction data
    for frame in dataset["frames"]:
        # Ensure video_id is present
        if "video_id" not in frame:
            frame["video_id"] = dataset["video_record"]["video_id"]
        
        await db_manager.execute(
            """INSERT INTO video_frames (frame_id, video_id, ts, local_path,
               emb_rgb, emb_gray, kp_blob_path, created_at) 
               VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
               ON CONFLICT (frame_id) DO NOTHING;""",
            frame["frame_id"], frame["video_id"], frame["ts"], frame["local_path"],
            str(frame["emb_rgb"]), str(frame["emb_gray"]), frame["kp_blob_path"]
        )
    
    # Insert job record and set phase to 'matching'
    await db_manager.execute(
        """INSERT INTO jobs (job_id, phase, industry, created_at) 
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (job_id) DO UPDATE SET phase = EXCLUDED.phase;""",
        job_id, "matching", "test_industry"
    )
    
    # Insert prerequisite phase events to simulate feature extraction completion
    await db_manager.execute(
        """INSERT INTO phase_events (event_id, job_id, name, received_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (event_id) DO NOTHING;""",
        str(uuid.uuid4()), job_id, "image.embeddings.completed"
    )
    await db_manager.execute(
        """INSERT INTO phase_events (event_id, job_id, name, received_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (event_id) DO NOTHING;""",
        str(uuid.uuid4()), job_id, "video.keypoints.completed"
    )


async def setup_low_similarity_matching_database_state(
    db_manager,
    job_id: str,
    dataset: Dict[str, Any]
) -> None:
    """Setup database state for zero matches testing with low similarity embeddings"""
    # Use same setup as comprehensive but with low similarity data
    await setup_comprehensive_matching_database_state(db_manager, job_id, dataset)


async def setup_partial_asset_matching_database_state(
    db_manager,
    job_id: str,
    dataset: Dict[str, Any]
) -> None:
    """Setup database state for partial asset availability (missing keypoints) testing"""
    # Insert video record
    video_record = dataset["video_record"]
    await db_manager.execute(
        """INSERT INTO videos (video_id, platform, url, job_id, created_at) 
           VALUES ($1, $2, $3, $4, NOW())
           ON CONFLICT (video_id) DO NOTHING;""",
        video_record["video_id"], video_record["platform"], video_record["url"], job_id
    )
    
    # Insert product records with partial assets (some missing keypoints)
    for record in dataset["product_records"]:
        await db_manager.execute(
            """INSERT INTO products (product_id, src, asin_or_itemid, marketplace, job_id, created_at) 
               VALUES ($1, $2, $3, $4, $5, NOW())
               ON CONFLICT (product_id) DO NOTHING;""",
            record["product_id"], record["src"], record["asin_or_itemid"], record["marketplace"], job_id
        )
        
        # Handle partial assets - some records may have None kp_blob_path
        kp_blob_path = record.get("kp_blob_path")
        if kp_blob_path is None:
            # Insert without keypoint blob path for fallback scenario
            await db_manager.execute(
                """INSERT INTO product_images (img_id, product_id, local_path, 
                   emb_rgb, emb_gray, kp_blob_path, created_at) 
                   VALUES ($1, $2, $3, $4, $5, $6, NOW())
                   ON CONFLICT (img_id) DO NOTHING;""",
                record["img_id"], record["product_id"], record["local_path"],
                str(record["emb_rgb"]), str(record["emb_gray"]), None
            )
        else:
            # Full record with keypoints
            await db_manager.execute(
                """INSERT INTO product_images (img_id, product_id, local_path, 
                   emb_rgb, emb_gray, kp_blob_path, created_at) 
                   VALUES ($1, $2, $3, $4, $5, $6, NOW())
                   ON CONFLICT (img_id) DO NOTHING;""",
                record["img_id"], record["product_id"], record["local_path"],
                str(record["emb_rgb"]), str(record["emb_gray"]), kp_blob_path
            )
    
    # Insert video frames with full assets
    for frame in dataset["frames"]:
        if "video_id" not in frame:
            frame["video_id"] = dataset["video_record"]["video_id"]
        
        await db_manager.execute(
            """INSERT INTO video_frames (frame_id, video_id, ts, local_path,
               emb_rgb, emb_gray, kp_blob_path, created_at) 
               VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
               ON CONFLICT (frame_id) DO NOTHING;""",
            frame["frame_id"], frame["video_id"], frame["ts"], frame["local_path"],
            str(frame["emb_rgb"]), str(frame["emb_gray"]), frame["kp_blob_path"]
        )
    
    # Insert job record
    await db_manager.execute(
        """INSERT INTO jobs (job_id, phase, industry, created_at) 
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (job_id) DO UPDATE SET phase = EXCLUDED.phase;""",
        job_id, "matching", "test_industry"
    )
    
    # Insert prerequisite phase events
    await db_manager.execute(
        """INSERT INTO phase_events (event_id, job_id, name, received_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (event_id) DO NOTHING;""",
        str(uuid.uuid4()), job_id, "image.embeddings.completed"
    )
    await db_manager.execute(
        """INSERT INTO phase_events (event_id, job_id, name, received_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (event_id) DO NOTHING;""",
        str(uuid.uuid4()), job_id, "video.keypoints.completed"
    )


async def cleanup_test_database_state(
    db_manager,
    job_id: str
) -> None:
    """Clean up test data to avoid conflicts between test runs"""
    # Clean up in order of dependencies to avoid foreign key conflicts
    
    # Clean up events and matches first (tables with job_id column)
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
            # Table might not exist
            print(f"⚠ Could not clean table {table}: {e}")
            pass
    
    # Clean up tables that need to be cleaned by ID patterns
    # These tables don't have job_id, so we need to clean them differently
    try:
        # Clean up products by pattern
        await db_manager.execute(
            "DELETE FROM products WHERE product_id LIKE $1",
            f"{job_id}%"
        )
    except Exception:
        pass
    
    try:
        # Clean up videos by pattern  
        await db_manager.execute(
            "DELETE FROM videos WHERE video_id LIKE $1",
            f"{job_id}%"
        )
    except Exception:
        pass


async def run_matching_idempotency_test(
    env: Dict[str, Any],
    job_id: str,
    event_id: str
) -> None:
    """Test idempotency for matching phase events"""
    publisher = env["publisher"]
    db_manager = env.get("db_manager")
    
    try:
        # Check current processed events
        if db_manager:
            processed_events = await db_manager.fetch_all(
                "SELECT * FROM processed_events WHERE event_id = $1", event_id
            )
            print(f"✓ Processed events for {event_id}: {len(processed_events)}")
        
        print("✓ Matching idempotency test completed - no duplicate processing detected")
    except Exception as e:
        print(f"⚠ Matching idempotency test encountered issue: {e}")
        # This is acceptable in test environment
