from typing import Optional, List, Dict, Any
import uuid
from .database import DatabaseManager
from .models import Product, ProductImage, Video, VideoFrame, Match


class ProductCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_product(self, product: Product) -> str:
        """Create a new product"""
        query = """
        INSERT INTO products (product_id, src, asin_or_itemid, title, brand, url)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING product_id
        """
        return await self.db.fetch_val(
            query, product.product_id, product.src, product.asin_or_itemid,
            product.title, product.brand, product.url
        )
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        query = "SELECT * FROM products WHERE product_id = $1"
        row = await self.db.fetch_one(query, product_id)
        return Product(**row) if row else None
    
    async def list_products(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """List products with pagination"""
        query = "SELECT * FROM products ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        rows = await self.db.fetch_all(query, limit, offset)
        return [Product(**row) for row in rows]


class ProductImageCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_product_image(self, image: ProductImage) -> str:
        """Create a new product image"""
        query = """
        INSERT INTO product_images (img_id, product_id, local_path, kp_blob_path, phash)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING img_id
        """
        return await self.db.fetch_val(
            query, image.img_id, image.product_id, image.local_path,
            image.kp_blob_path, image.phash
        )
    
    async def update_embeddings(self, img_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Update embeddings for a product image"""
        # Convert lists to vector format for PostgreSQL
        rgb_vector = '[' + ','.join(map(str, emb_rgb)) + ']'
        gray_vector = '[' + ','.join(map(str, emb_gray)) + ']'
        
        query = """
        UPDATE product_images 
        SET emb_rgb = $2::vector, emb_gray = $3::vector
        WHERE img_id = $1
        """
        await self.db.execute(query, img_id, rgb_vector, gray_vector)
    
    async def get_product_image(self, img_id: str) -> Optional[ProductImage]:
        """Get a product image by ID"""
        query = "SELECT * FROM product_images WHERE img_id = $1"
        row = await self.db.fetch_one(query, img_id)
        return ProductImage(**row) if row else None
    
    async def list_product_images(self, product_id: str) -> List[ProductImage]:
        """List images for a product"""
        query = "SELECT * FROM product_images WHERE product_id = $1"
        rows = await self.db.fetch_all(query, product_id)
        return [ProductImage(**row) for row in rows]


class VideoCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_video(self, video: Video) -> str:
        """Create a new video"""
        query = """
        INSERT INTO videos (video_id, platform, url, title, duration_s, published_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING video_id
        """
        return await self.db.fetch_val(
            query, video.video_id, video.platform, video.url,
            video.title, video.duration_s, video.published_at
        )
    
    async def get_video(self, video_id: str) -> Optional[Video]:
        """Get a video by ID"""
        query = "SELECT * FROM videos WHERE video_id = $1"
        row = await self.db.fetch_one(query, video_id)
        return Video(**row) if row else None
    
    async def list_videos(self, limit: int = 100, offset: int = 0) -> List[Video]:
        """List videos with pagination"""
        query = "SELECT * FROM videos ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        rows = await self.db.fetch_all(query, limit, offset)
        return [Video(**row) for row in rows]


class VideoFrameCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_video_frame(self, frame: VideoFrame) -> str:
        """Create a new video frame"""
        query = """
        INSERT INTO video_frames (frame_id, video_id, ts, local_path, kp_blob_path)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING frame_id
        """
        return await self.db.fetch_val(
            query, frame.frame_id, frame.video_id, frame.ts,
            frame.local_path, frame.kp_blob_path
        )
    
    async def update_embeddings(self, frame_id: str, emb_rgb: List[float], emb_gray: List[float]):
        """Update embeddings for a video frame"""
        # Convert lists to vector format for PostgreSQL
        rgb_vector = '[' + ','.join(map(str, emb_rgb)) + ']'
        gray_vector = '[' + ','.join(map(str, emb_gray)) + ']'
        
        query = """
        UPDATE video_frames 
        SET emb_rgb = $2::vector, emb_gray = $3::vector
        WHERE frame_id = $1
        """
        await self.db.execute(query, frame_id, rgb_vector, gray_vector)
    
    async def get_video_frame(self, frame_id: str) -> Optional[VideoFrame]:
        """Get a video frame by ID"""
        query = "SELECT * FROM video_frames WHERE frame_id = $1"
        row = await self.db.fetch_one(query, frame_id)
        return VideoFrame(**row) if row else None
    
    async def list_video_frames(self, video_id: str) -> List[VideoFrame]:
        """List frames for a video"""
        query = "SELECT * FROM video_frames WHERE video_id = $1 ORDER BY ts"
        rows = await self.db.fetch_all(query, video_id)
        return [VideoFrame(**row) for row in rows]


class MatchCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_match(self, match: Match) -> str:
        """Create a new match"""
        query = """
        INSERT INTO matches (match_id, job_id, product_id, video_id, best_img_id, best_frame_id, ts, score, evidence_path)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING match_id
        """
        return await self.db.fetch_val(
            query, match.match_id, match.job_id, match.product_id, match.video_id,
            match.best_img_id, match.best_frame_id, match.ts, match.score, match.evidence_path
        )
    
    async def get_match(self, match_id: str) -> Optional[Match]:
        """Get a match by ID"""
        query = "SELECT * FROM matches WHERE match_id = $1"
        row = await self.db.fetch_one(query, match_id)
        return Match(**row) if row else None
    
    async def list_matches(self, job_id: Optional[str] = None, min_score: Optional[float] = None, 
                          limit: int = 100, offset: int = 0) -> List[Match]:
        """List matches with optional filtering"""
        conditions = []
        params = []
        param_count = 0
        
        if job_id:
            param_count += 1
            conditions.append(f"job_id = ${param_count}")
            params.append(job_id)
        
        if min_score is not None:
            param_count += 1
            conditions.append(f"score >= ${param_count}")
            params.append(min_score)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        param_count += 1
        params.append(limit)
        param_count += 1
        params.append(offset)
        
        query = f"""
        SELECT * FROM matches 
        {where_clause}
        ORDER BY score DESC, created_at DESC 
        LIMIT ${param_count-1} OFFSET ${param_count}
        """
        
        rows = await self.db.fetch_all(query, *params)
        return [Match(**row) for row in rows]