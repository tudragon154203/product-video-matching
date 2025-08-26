"""
Results service layer for main-api.
Contains business logic for product-video matching results.
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import logging
from datetime import datetime, timezone
import pytz

from common_py.database import DatabaseManager
from common_py.crud import ProductCRUD, VideoCRUD, MatchCRUD
from models.results_schemas import (
    MatchResponse, MatchDetailResponse, StatsResponse, 
    ProductResponse, VideoResponse, MatchListResponse
)

logger = logging.getLogger(__name__)


class ResultsService:
    """Results service for match-related business logic"""
    
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
    
    def _get_gmt7_time(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert datetime to GMT+7 timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(pytz.timezone('Asia/Saigon'))
    
    async def get_results(
        self,
        industry: Optional[str] = None,
        min_score: Optional[float] = None,
        job_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> MatchListResponse:
        """
        Get matching results with optional filtering.
        
        Args:
            industry: Filter by industry
            min_score: Minimum match score
            job_id: Filter by job ID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            MatchListResponse with paginated match data
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
            
            # Get total count for pagination
            total = await self.match_crud.count_matches(
                job_id=job_id,
                min_score=min_score
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
            
            return MatchListResponse(
                items=enriched_matches,
                total=total,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(
                f"Failed to get results: {e}",
                extra={"correlation_id": correlation_id}
            )
            raise

    async def _enrich_match_data(
        self, 
        match: Any, 
        industry: Optional[str],
        correlation_id: str
    ) -> Optional[MatchResponse]:
        """
        Enrich match data with product and video information.
        
        Args:
            match: Match object
            industry: Industry filter
            correlation_id: Request correlation ID
            
        Returns:
            MatchResponse or None if filtered out
        """
        try:
            product = await self.product_crud.get_product(match.product_id)
            video = await self.video_crud.get_video(match.video_id)
            
            # Apply industry filter
            if industry and product and industry.lower() not in (product.title or "").lower():
                return None
            
            return MatchResponse(
                match_id=match.match_id,
                job_id=match.job_id,
                product_id=match.product_id,
                video_id=match.video_id,
                best_img_id=match.best_img_id,
                best_frame_id=match.best_frame_id,
                ts=match.ts,
                score=match.score,
                evidence_path=match.evidence_path,
                created_at=match.created_at.isoformat() if match.created_at else "",
                product_title=product.title if product else None,
                video_title=video.title if video else None,
                video_platform=video.platform if video else None
            )
            
        except Exception as e:
            logger.error(
                f"Failed to enrich match data: {e}",
                extra={"correlation_id": correlation_id, "match_id": match.match_id}
            )
            raise
    
    async def get_match(self, match_id: str) -> Optional[MatchDetailResponse]:
        """
        Get detailed match information.
        
        Args:
            match_id: Match ID
            
        Returns:
            MatchDetailResponse or None if not found
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
            
            result = MatchDetailResponse(
                match_id=match.match_id,
                job_id=match.job_id,
                best_img_id=match.best_img_id,
                best_frame_id=match.best_frame_id,
                ts=match.ts,
                score=match.score,
                evidence_path=match.evidence_path,
                created_at=match.created_at.isoformat() if match.created_at else "",
                product=ProductResponse(
                    product_id=product.product_id,
                    src=product.src,
                    asin_or_itemid=product.asin_or_itemid,
                    title=product.title,
                    brand=product.brand,
                    url=product.url,
                    created_at=product.created_at.isoformat() if product.created_at else "",
                    image_count=product_image_count
                ),
                video=VideoResponse(
                    video_id=video.video_id,
                    platform=video.platform,
                    url=video.url,
                    title=video.title,
                    duration_s=video.duration_s,
                    published_at=video.published_at.isoformat() if video.published_at else None,
                    created_at=video.created_at.isoformat() if video.created_at else "",
                    frame_count=video_frame_count
                )
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
            raise

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
            raise

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
            raise
    
    async def get_evidence_path(self, match_id: str) -> Optional[str]:
        """
        Get evidence image path for a match.
        
        Args:
            match_id: Match ID
            
        Returns:
            Evidence path or None if not found
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
            raise
    
    async def get_stats(self) -> StatsResponse:
        """
        Get system statistics.
        
        Returns:
            StatsResponse with system statistics
        """
        correlation_id = str(uuid4())
        
        try:
            logger.info(
                "Getting system statistics",
                extra={"correlation_id": correlation_id}
            )
            
            stats = StatsResponse(
                products=await self.db.fetch_val("SELECT COUNT(*) FROM products") or 0,
                product_images=await self.db.fetch_val("SELECT COUNT(*) FROM product_images") or 0,
                videos=await self.db.fetch_val("SELECT COUNT(*) FROM videos") or 0,
                video_frames=await self.db.fetch_val("SELECT COUNT(*) FROM video_frames") or 0,
                matches=await self.db.fetch_val("SELECT COUNT(*) FROM matches") or 0,
                jobs=await self.db.fetch_val("SELECT COUNT(*) FROM jobs") or 0
            )
            
            logger.info(
                "Retrieved system statistics",
                extra={"correlation_id": correlation_id, "stats": stats.dict()}
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                f"Failed to get stats: {e}",
                extra={"correlation_id": correlation_id}
            )
            raise