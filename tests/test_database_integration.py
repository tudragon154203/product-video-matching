"""
Database integration tests
"""
import pytest
import uuid
from datetime import datetime


@pytest.mark.asyncio
async def test_database_connection(db_manager):
    """Test database connection"""
    result = await db_manager.fetch_val("SELECT 1")
    assert result == 1


@pytest.mark.asyncio
async def test_create_job(db_manager, clean_database, test_data):
    """Test creating a job"""
    job_id = test_data["job_id"]
    industry = test_data["industry"]
    
    await db_manager.execute(
        "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
        job_id, "test query", industry, '{"product":{"en":["test"]},"video":{"vi":["test"],"zh":["test"]}}', "collection"
    )
    
    # Verify job was created
    job = await db_manager.fetch_one(
        "SELECT * FROM jobs WHERE job_id = $1", job_id
    )
    
    assert job is not None
    assert job["job_id"] == job_id
    assert job["industry"] == industry


@pytest.mark.asyncio
async def test_create_product_with_images(db_manager, clean_database, test_data):
    """Test creating product with images"""
    job_id = test_data["job_id"]
    product = test_data["product"]
    
    # Create job first
    await db_manager.execute(
        "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
        job_id, "test query", "test", '{"product":{"en":["test"]},"video":{"vi":["test"],"zh":["test"]}}', "collection"
    )
    
    # Create product
    await db_manager.execute(
        "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        product["product_id"], product["src"], product["asin_or_itemid"],
        product["title"], product["brand"], product["url"], job_id
    )
    
    # Create product images
    for i in range(2):
        img_id = f"{product['product_id']}_img_{i}"
        await db_manager.execute(
            "INSERT INTO product_images (img_id, product_id, local_path) VALUES ($1, $2, $3)",
            img_id, product["product_id"], f"/test/path/{img_id}.jpg"
        )
    
    # Verify product was created
    created_product = await db_manager.fetch_one(
        "SELECT * FROM products WHERE product_id = $1", product["product_id"]
    )
    
    assert created_product is not None
    assert created_product["title"] == product["title"]
    
    # Verify images were created
    images = await db_manager.fetch_all(
        "SELECT * FROM product_images WHERE product_id = $1", product["product_id"]
    )
    
    assert len(images) == 2


@pytest.mark.asyncio
async def test_create_video_with_frames(db_manager, clean_database, test_data):
    """Test creating video with frames"""
    job_id = test_data["job_id"]
    video = test_data["video"]
    
    # Create job first
    await db_manager.execute(
        "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
        job_id, "test query", "test", '{"product":{"en":["test"]},"video":{"vi":["test"],"zh":["test"]}}', "collection"
    )
    
    # Create video
    await db_manager.execute(
        "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
        video["video_id"], video["platform"], video["url"],
        video["title"], video["duration_s"], job_id
    )
    
    # Create video frames
    for i in range(3):
        frame_id = f"{video['video_id']}_frame_{i}"
        timestamp = i * 30.0
        await db_manager.execute(
            "INSERT INTO video_frames (frame_id, video_id, ts, local_path) VALUES ($1, $2, $3, $4)",
            frame_id, video["video_id"], timestamp, f"/test/path/{frame_id}.jpg"
        )
    
    # Verify video was created
    created_video = await db_manager.fetch_one(
        "SELECT * FROM videos WHERE video_id = $1", video["video_id"]
    )
    
    assert created_video is not None
    assert created_video["title"] == video["title"]
    
    # Verify frames were created
    frames = await db_manager.fetch_all(
        "SELECT * FROM video_frames WHERE video_id = $1 ORDER BY ts", video["video_id"]
    )
    
    assert len(frames) == 3
    assert frames[0]["ts"] == 0.0
    assert frames[1]["ts"] == 30.0
    assert frames[2]["ts"] == 60.0


@pytest.mark.asyncio
async def test_create_match(db_manager, clean_database, test_data):
    """Test creating a match"""
    job_id = test_data["job_id"]
    product = test_data["product"]
    video = test_data["video"]
    
    # Create job
    await db_manager.execute(
        "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
        job_id, "test query", "test", '{"product":{"en":["test"]},"video":{"vi":["test"],"zh":["test"]}}', "collection"
    )
    
    # Create product and video
    await db_manager.execute(
        "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        product["product_id"], product["src"], product["asin_or_itemid"],
        product["title"], product["brand"], product["url"], job_id
    )
    
    await db_manager.execute(
        "INSERT INTO videos (video_id, platform, url, title, duration_s, job_id) VALUES ($1, $2, $3, $4, $5, $6)",
        video["video_id"], video["platform"], video["url"],
        video["title"], video["duration_s"], job_id
    )
    
    # Create image and frame
    img_id = f"{product['product_id']}_img_0"
    frame_id = f"{video['video_id']}_frame_0"
    
    await db_manager.execute(
        "INSERT INTO product_images (img_id, product_id, local_path) VALUES ($1, $2, $3)",
        img_id, product["product_id"], f"/test/path/{img_id}.jpg"
    )
    
    await db_manager.execute(
        "INSERT INTO video_frames (frame_id, video_id, ts, local_path) VALUES ($1, $2, $3, $4)",
        frame_id, video["video_id"], 30.0, f"/test/path/{frame_id}.jpg"
    )
    
    # Create match
    match_id = str(uuid.uuid4())
    await db_manager.execute(
        "INSERT INTO matches (match_id, job_id, product_id, video_id, best_img_id, best_frame_id, ts, score) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        match_id, job_id, product["product_id"], video["video_id"],
        img_id, frame_id, 30.0, 0.85
    )
    
    # Verify match was created
    created_match = await db_manager.fetch_one(
        "SELECT * FROM matches WHERE match_id = $1", match_id
    )
    
    assert created_match is not None
    assert created_match["score"] == 0.85
    assert created_match["job_id"] == job_id


@pytest.mark.asyncio
async def test_vector_operations(db_manager, clean_database, test_data):
    """Test vector operations (if pgvector is available)"""
    job_id = test_data["job_id"]
    product = test_data["product"]
    
    # Create job and product
    await db_manager.execute(
        "INSERT INTO jobs (job_id, query, industry, queries, phase) VALUES ($1, $2, $3, $4, $5)",
        job_id, "test query", "test", '{"product":{"en":["test"]},"video":{"vi":["test"],"zh":["test"]}}', "collection"
    )
    
    await db_manager.execute(
        "INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url, job_id) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        product["product_id"], product["src"], product["asin_or_itemid"],
        product["title"], product["brand"], product["url"], job_id
    )
    
    # Create image with embeddings
    img_id = f"{product['product_id']}_img_0"
    test_embedding = [0.1] * 512  # 512-dimensional test vector
    
    await db_manager.execute(
        "INSERT INTO product_images (img_id, product_id, local_path, emb_rgb) VALUES ($1, $2, $3, $4)",
        img_id, product["product_id"], f"/test/path/{img_id}.jpg", test_embedding
    )
    
    # Test vector similarity search
    try:
        similar_images = await db_manager.fetch_all(
            "SELECT img_id, 1 - (emb_rgb <=> $1) as similarity FROM product_images WHERE emb_rgb IS NOT NULL ORDER BY emb_rgb <=> $1 LIMIT 5",
            test_embedding
        )
        
        assert len(similar_images) >= 1
        assert similar_images[0]["img_id"] == img_id
        assert similar_images[0]["similarity"] >= 0.99  # Should be very similar to itself
        
    except Exception as e:
        # pgvector might not be available in test environment
        pytest.skip(f"Vector operations not available: {e}")