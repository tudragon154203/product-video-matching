import os
from typing import Optional, List, Dict, Any
from common_py.database import DatabaseManager
from common_py.crud import ProductCRUD, VideoCRUD, MatchCRUD
from common_py.logging_config import configure_logging

logger = configure_logging("results-api")


class ResultsService:
    """Main service class for results API"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.product_crud = ProductCRUD(db)
        self.video_crud = VideoCRUD(db)
        self.match_crud = MatchCRUD(db)
    
    async def get_results(
        self,
        industry: Optional[str] = None,
        min_score: Optional[float] = None,
        job_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get matching results with optional filtering"""
        try:
            matches = await self.match_crud.list_matches(
                job_id=job_id,
                min_score=min_score,
                limit=limit,
                offset=offset
            )
            
            enriched_matches = []
            for match in matches:
                enriched_match = await self._enrich_match_data(match, industry)
                if enriched_match:
                    enriched_matches.append(enriched_match)
            
            logger.info("Retrieved results", 
                       count=len(enriched_matches), 
                       industry=industry, 
                       min_score=min_score)
            
            return enriched_matches
            
        except Exception as e:
            logger.error("Failed to get results", error=str(e))
            raise

    async def _enrich_match_data(self, match: Any, industry: Optional[str]) -> Optional[Dict[str, Any]]:
        product = await self.product_crud.get_product(match.product_id)
        video = await self.video_crud.get_video(match.video_id)
        
        if industry and product and industry.lower() not in (product.title or "").lower():
            return None
        
        return {
            "match_id": match.match_id,
            "job_id": match.job_id,
            "product_id": match.product_id,
            "video_id": match.video_id,
            "best_img_id": match.best_img_id,
            "best_frame_id": match.best_frame_id,
            "ts": match.ts,
            "score": match.score,
            "evidence_path": match.evidence_path,
            "created_at": match.created_at.isoformat() if match.created_at else "",
            "product_title": product.title if product else None,
            "video_title": video.title if video else None,
            "video_platform": video.platform if video else None
        }
    
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed product information"""
        try:
            product = await self.product_crud.get_product(product_id)
            if not product:
                return None
            
            image_count = await self._get_product_image_count(product_id)
            
            return self._format_product_details(product, image_count)
            
        except Exception as e:
            logger.error("Failed to get product", product_id=product_id, error=str(e))
            raise

    async def _get_product_image_count(self, product_id: str) -> int:
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
            product_id
        ) or 0

    def _format_product_details(self, product: Any, image_count: int) -> Dict[str, Any]:
        return {
            "product_id": product.product_id,
            "src": product.src,
            "asin_or_itemid": product.asin_or_itemid,
            "title": product.title,
            "brand": product.brand,
            "url": product.url,
            "created_at": product.created_at.isoformat() if product.created_at else "",
            "image_count": image_count
        }
    
    async def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed video information"""
        try:
            video = await self.video_crud.get_video(video_id)
            if not video:
                return None
            
            frame_count = await self._get_video_frame_count(video_id)
            
            return self._format_video_details(video, frame_count)
            
        except Exception as e:
            logger.error("Failed to get video", video_id=video_id, error=str(e))
            raise

    async def _get_video_frame_count(self, video_id: str) -> int:
        return await self.db.fetch_val(
            "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
            video_id
        ) or 0

    def _format_video_details(self, video: Any, frame_count: int) -> Dict[str, Any]:
        return {
            "video_id": video.video_id,
            "platform": video.platform,
            "url": video.url,
            "title": video.title,
            "duration_s": video.duration_s,
            "published_at": video.published_at.isoformat() if video.published_at else None,
            "created_at": video.created_at.isoformat() if video.created_at else "",
            "frame_count": frame_count
        }
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed match information"""
        try:
            match = await self.match_crud.get_match(match_id)
            if not match:
                return None
            
            product, video = await self._get_match_related_entities(match)
            if not product or not video:
                return None
            
            product_image_count, video_frame_count = await self._get_match_asset_counts(match)
            
            return self._format_match_details(match, product, video, product_image_count, video_frame_count)
            
        except Exception as e:
            logger.error("Failed to get match", match_id=match_id, error=str(e))
            raise

    async def _get_match_related_entities(self, match: Any) -> tuple[Any, Any]:
        product = await self.product_crud.get_product(match.product_id)
        video = await self.video_crud.get_video(match.video_id)
        return product, video

    async def _get_match_asset_counts(self, match: Any) -> tuple[int, int]:
        product_image_count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
            match.product_id
        ) or 0
        
        video_frame_count = await self.db.fetch_val(
            "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
            match.video_id
        ) or 0
        return product_image_count, video_frame_count

    def _format_match_details(self, match: Any, product: Any, video: Any, product_image_count: int, video_frame_count: int) -> Dict[str, Any]:
        return {
            "match_id": match.match_id,
            "job_id": match.job_id,
            "product": {
                "product_id": product.product_id,
                "src": product.src,
                "asin_or_itemid": product.asin_or_itemid,
                "title": product.title,
                "brand": product.brand,
                "url": product.url,
                "created_at": product.created_at.isoformat() if product.created_at else "",
                "image_count": product_image_count
            },
            "video": {
                "video_id": video.video_id,
                "platform": video.platform,
                "url": video.url,
                "title": video.title,
                "duration_s": video.duration_s,
                "published_at": video.published_at.isoformat() if video.published_at else None,
                "created_at": video.created_at.isoformat() if video.created_at else "",
                "frame_count": video_frame_count
            },
            "best_img_id": match.best_img_id,
            "best_frame_id": match.best_frame_id,
            "ts": match.ts,
            "score": match.score,
            "evidence_path": match.evidence_path,
            "created_at": match.created_at.isoformat() if match.created_at else ""
        }
    
    async def get_evidence_path(self, match_id: str) -> Optional[str]:
        """Get evidence image path for a match"""
        try:
            match = await self.match_crud.get_match(match_id)
            if not match or not match.evidence_path:
                return None
            
            # Check if file exists
            if not os.path.exists(match.evidence_path):
                return None
            
            return match.evidence_path
            
        except Exception as e:
            logger.error("Failed to get evidence path", match_id=match_id, error=str(e))
            raise
    
    async def get_stats(self) -> Dict[str, int]:
        """Get system statistics"""
        try:
            stats = {
                "products": await self.db.fetch_val("SELECT COUNT(*) FROM products") or 0,
                "product_images": await self.db.fetch_val("SELECT COUNT(*) FROM product_images") or 0,
                "videos": await self.db.fetch_val("SELECT COUNT(*) FROM videos") or 0,
                "video_frames": await self.db.fetch_val("SELECT COUNT(*) FROM video_frames") or 0,
                "matches": await self.db.fetch_val("SELECT COUNT(*) FROM matches") or 0,
                "jobs": await self.db.fetch_val("SELECT COUNT(*) FROM jobs") or 0
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get stats", error=str(e))
            raise