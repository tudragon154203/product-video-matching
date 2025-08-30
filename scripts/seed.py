import os
import sys
import uuid
import random
from datetime import datetime, timezone
from pathlib import Path

# Add the project root and libs/common-py to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "libs" / "common-py"))

from libs.config import config
from common_py.database import DatabaseManager
from common_py.crud.video_crud import VideoCRUD
from common_py.crud.video_frame_crud import VideoFrameCRUD
from common_py.crud.product_crud import ProductCRUD
from common_py.crud.product_image_crud import ProductImageCRUD

from faker import Faker

fake = Faker()

async def seed_data():
    db_manager = DatabaseManager(config.POSTGRES_DSN)
    await db_manager.connect()

    video_crud = VideoCRUD(db_manager)
    video_frame_crud = VideoFrameCRUD(db_manager)
    product_crud = ProductCRUD(db_manager)
    product_image_crud = ProductImageCRUD(db_manager)

    try:
        # Clear existing data (optional, but good for consistent seeding)
        print("Truncating existing data...")
        await db_manager.execute("TRUNCATE TABLE video_frames, product_images, videos, products RESTART IDENTITY CASCADE;")
        print("Data truncated.")

        job_id = str(uuid.uuid4())
        print(f"Seeding data for job_id: {job_id}")

        # Seed Products
        products = []
        for _ in range(5):
            product_id = str(uuid.uuid4())
            product = await product_crud.create_product(
                product_id=product_id,
                job_id=job_id,
                title=fake.catch_phrase(),
                description=fake.paragraph(),
                price=random.uniform(10.0, 500.0),
                currency="USD",
                product_url=fake.url(),
                source_platform="ecommerce"
            )
            products.append(product)
            print(f"  Created product: {product.product_id}")

            # Seed Product Images for each product
            for _ in range(random.randint(1, 3)):
                img_id = str(uuid.uuid4())
                # Store local_path relative to DATA_ROOT_CONTAINER
                relative_path = f"product_images/{product_id}/image_{img_id}.jpg"
                await product_image_crud.create_product_image(
                    img_id=img_id,
                    product_id=product_id,
                    job_id=job_id,
                    url=fake.image_url(), # External URL
                    local_path=relative_path, # Relative path
                    source_platform="ecommerce"
                )
                print(f"    Created product image: {img_id} (local_path: {relative_path})")

        # Seed Videos
        videos = []
        for _ in range(3):
            video_id = str(uuid.uuid4())
            video = await video_crud.create_video(
                video_id=video_id,
                job_id=job_id,
                platform=random.choice(["youtube", "tiktok"]),
                url=fake.url(),
                title=fake.sentence(),
                description=fake.paragraph(),
                duration_s=random.randint(60, 600)
            )
            videos.append(video)
            print(f"  Created video: {video.video_id}")

            # Seed Video Frames for each video
            for i in range(random.randint(5, 15)):
                frame_id = str(uuid.uuid4())
                # Store local_path relative to DATA_ROOT_CONTAINER
                relative_path = f"keyframes/{video_id}/frame_{i}.jpg"
                await video_frame_crud.create_video_frame(
                    frame_id=frame_id,
                    video_id=video_id,
                    job_id=job_id,
                    ts=i * 1000, # Milliseconds
                    url=fake.image_url(), # External URL
                    local_path=relative_path, # Relative path
                    source_platform="video_crawler"
                )
                print(f"    Created video frame: {frame_id} (local_path: {relative_path})")

        print("Seeding complete!")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")
    finally:
        await db_manager.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_data())