from typing import Optional, List, Dict, Any
from ..database import DatabaseManager
from ..models import Match

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
