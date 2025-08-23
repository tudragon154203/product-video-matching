"""
Results service layer with improved error handling and dependency injection.
Contains business logic for product-video matching results.
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import logging

from common_py.database import DatabaseManager
from common_py.crud import ProductCRUD, VideoCRUD, MatchCRUD
from core.exceptions import DatabaseError, ResourceNotFound, ServiceError

logger = logging.getLogger(__name__)


class ResultsService:
    """Main service class for results API with improved error handling"""
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize the results service.
        
        Args:
            db: Database manager instance
        """
        self.db = db
        self.product_crud = ProductCRUD(db)
        self.video_crud = VideoCRUD(db)
        self.match_crud = MatchCRUD(db)
        
        logger.info("ResultsService initialized")
    
    async def get_results(
        self,
        industry: Optional[str] = None,
        min_score: Optional[float] = None,
        job_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get matching results with optional filtering.
        
        Args:
            industry: Filter by industry
            min_score: Minimum match score
            job_id: Filter by job ID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of enriched match data
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                "Getting results",
                extra={
                    "correlation_id": correlation_id,
                    "industry": industry,
                    "min_score": min_score,
                    "job_id": job_id,
                    "limit": limit,
                    "offset": offset
                }
            )
            
            matches = await self.match_crud.list_matches(
                job_id=job_id,
                min_score=min_score,
                limit=limit,
                offset=offset
            )
            
            enriched_matches = []
            for match in matches:
                try:
                    enriched_match = await self._enrich_match_data(match, industry, correlation_id)
                    if enriched_match:
                        enriched_matches.append(enriched_match)
                except Exception as e:
                    logger.warning(
                        f"Failed to enrich match data for match {match.match_id}: {e}",
                        extra={"correlation_id": correlation_id}
                    )
                    # Continue processing other matches
                    continue
            
            logger.info(
                f"Retrieved {len(enriched_matches)} results",
                extra={
                    "correlation_id": correlation_id,
                    "count": len(enriched_matches)
                }
            )
            
            return enriched_matches
            
        except Exception as e:
            logger.error(
                f"Failed to get results: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get results: {e}", correlation_id)

    async def _enrich_match_data(
        self, 
        match: Any, 
        industry: Optional[str],
        correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich match data with product and video information.
        
        Args:
            match: Match object
            industry: Industry filter
            correlation_id: Request correlation ID
            
        Returns:
            Enriched match data or None if filtered out
        """
        try:
            product = await self.product_crud.get_product(match.product_id)
            video = await self.video_crud.get_video(match.video_id)
            
            # Apply industry filter
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
            
        except Exception as e:
            logger.error(
                f"Failed to enrich match data: {e}",
                extra={"correlation_id": correlation_id, "match_id": match.match_id}
            )
            raise DatabaseError(f"Failed to enrich match data: {e}", correlation_id)
    
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed product information.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product details or None if not found
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                f"Getting product {product_id}",
                extra={"correlation_id": correlation_id, "product_id": product_id}
            )
            
            product = await self.product_crud.get_product(product_id)
            if not product:
                return None
            
            image_count = await self._get_product_image_count(product_id, correlation_id)
            
            result = self._format_product_details(product, image_count)
            
            logger.info(
                f"Retrieved product {product_id}",
                extra={"correlation_id": correlation_id}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to get product {product_id}: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get product: {e}", correlation_id)

    async def _get_product_image_count(self, product_id: str, correlation_id: str) -> int:
        """Get count of images for a product"""
        try:
            return await self.db.fetch_val(
                "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
                product_id
            ) or 0
        except Exception as e:
            logger.error(
                f"Failed to get product image count: {e}",
                extra={"correlation_id": correlation_id, "product_id": product_id}
            )
            raise DatabaseError(f"Failed to get product image count: {e}", correlation_id)

    def _format_product_details(self, product: Any, image_count: int) -> Dict[str, Any]:
        """Format product details for response"""
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
        """
        Get detailed video information.
        
        Args:
            video_id: Video ID
            
        Returns:
            Video details or None if not found
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                f"Getting video {video_id}",
                extra={"correlation_id": correlation_id, "video_id": video_id}
            )
            
            video = await self.video_crud.get_video(video_id)
            if not video:
                return None
            
            frame_count = await self._get_video_frame_count(video_id, correlation_id)
            
            result = self._format_video_details(video, frame_count)
            
            logger.info(
                f"Retrieved video {video_id}",
                extra={"correlation_id": correlation_id}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to get video {video_id}: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get video: {e}", correlation_id)

    async def _get_video_frame_count(self, video_id: str, correlation_id: str) -> int:
        """Get count of frames for a video"""
        try:
            return await self.db.fetch_val(
                "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
                video_id
            ) or 0
        except Exception as e:
            logger.error(
                f"Failed to get video frame count: {e}",
                extra={"correlation_id": correlation_id, "video_id": video_id}
            )
            raise DatabaseError(f"Failed to get video frame count: {e}", correlation_id)

    def _format_video_details(self, video: Any, frame_count: int) -> Dict[str, Any]:
        """Format video details for response"""
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
        """
        Get detailed match information.
        
        Args:
            match_id: Match ID
            
        Returns:
            Match details or None if not found
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                f"Getting match {match_id}",
                extra={"correlation_id": correlation_id, "match_id": match_id}
            )
            
            match = await self.match_crud.get_match(match_id)
            if not match:
                return None
            
            product, video = await self._get_match_related_entities(match, correlation_id)
            if not product or not video:
                return None
            
            product_image_count, video_frame_count = await self._get_match_asset_counts(
                match, correlation_id
            )
            
            result = self._format_match_details(
                match, product, video, product_image_count, video_frame_count
            )
            
            logger.info(
                f"Retrieved match {match_id}",
                extra={"correlation_id": correlation_id}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to get match {match_id}: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get match: {e}", correlation_id)

    async def _get_match_related_entities(
        self, 
        match: Any, 
        correlation_id: str
    ) -> Tuple[Any, Any]:
        """Get product and video entities for a match"""
        try:
            product = await self.product_crud.get_product(match.product_id)
            video = await self.video_crud.get_video(match.video_id)
            return product, video
        except Exception as e:
            logger.error(
                f"Failed to get match related entities: {e}",
                extra={"correlation_id": correlation_id, "match_id": match.match_id}
            )
            raise DatabaseError(f"Failed to get match related entities: {e}", correlation_id)

    async def _get_match_asset_counts(
        self, 
        match: Any, 
        correlation_id: str
    ) -> Tuple[int, int]:
        """Get asset counts for a match"""
        try:
            product_image_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM product_images WHERE product_id = $1",
                match.product_id
            ) or 0
            
            video_frame_count = await self.db.fetch_val(
                "SELECT COUNT(*) FROM video_frames WHERE video_id = $1",
                match.video_id
            ) or 0
            
            return product_image_count, video_frame_count
            
        except Exception as e:
            logger.error(
                f"Failed to get match asset counts: {e}",
                extra={"correlation_id": correlation_id, "match_id": match.match_id}
            )
            raise DatabaseError(f"Failed to get match asset counts: {e}", correlation_id)

    def _format_match_details(
        self, 
        match: Any, 
        product: Any, 
        video: Any, 
        product_image_count: int, 
        video_frame_count: int
    ) -> Dict[str, Any]:
        """Format match details for response"""
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
        """
        Get evidence image path for a match.
        
        Args:
            match_id: Match ID
            
        Returns:
            Evidence path or None if not found
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                f"Getting evidence path for match {match_id}",
                extra={"correlation_id": correlation_id, "match_id": match_id}
            )
            
            match = await self.match_crud.get_match(match_id)
            if not match or not match.evidence_path:
                return None
            
            # Check if file exists
            if not os.path.exists(match.evidence_path):
                logger.warning(
                    f"Evidence file not found: {match.evidence_path}",
                    extra={"correlation_id": correlation_id, "match_id": match_id}
                )
                return None
            
            logger.info(
                f"Retrieved evidence path for match {match_id}",
                extra={"correlation_id": correlation_id}
            )
            
            return match.evidence_path
            
        except Exception as e:
            logger.error(
                f"Failed to get evidence path for match {match_id}: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get evidence path: {e}", correlation_id)
    
    async def get_stats(self) -> Dict[str, int]:
        """
        Get system statistics.
        
        Returns:
            Dictionary of system statistics
            
        Raises:
            DatabaseError: If database operation fails
            ServiceError: If service operation fails
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                "Getting system statistics",
                extra={"correlation_id": correlation_id}
            )
            
            stats = {
                "products": await self.db.fetch_val("SELECT COUNT(*) FROM products") or 0,
                "product_images": await self.db.fetch_val("SELECT COUNT(*) FROM product_images") or 0,
                "videos": await self.db.fetch_val("SELECT COUNT(*) FROM videos") or 0,
                "video_frames": await self.db.fetch_val("SELECT COUNT(*) FROM video_frames") or 0,
                "matches": await self.db.fetch_val("SELECT COUNT(*) FROM matches") or 0,
                "jobs": await self.db.fetch_val("SELECT COUNT(*) FROM jobs") or 0
            }
            
            logger.info(
                "Retrieved system statistics",
                extra={"correlation_id": correlation_id, "stats": stats}
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                f"Failed to get stats: {e}",
                extra={"correlation_id": correlation_id}
            )
            if isinstance(e, DatabaseError):
                raise
            raise ServiceError(f"Failed to get stats: {e}", correlation_id)