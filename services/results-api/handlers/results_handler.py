from fastapi import FastAPI, HTTPException
from common_py.database import DatabaseManager
from config_loader import config
from services.service import ResultsService
from .decorators import handle_errors  # Add error handling decorator

class ResultsHandler:
    def __init__(self):
        self.db = DatabaseManager(config.POSTGRES_DSN)
        self.service = ResultsService(self.db)
        self.app = FastAPI(title="Results API", version="1.0.0")
        
        # Register routes
        self.app.add_api_route("/results", self.get_results, methods=["GET"])
        self.app.add_api_route("/products/{product_id}", self.get_product, methods=["GET"])
        self.app.add_api_route("/videos/{video_id}", self.get_video, methods=["GET"])
        self.app.add_api_route("/matches/{match_id}", self.get_match, methods=["GET"])
        self.app.add_api_route("/evidence/{match_id}", self.get_evidence_image, methods=["GET"])
        self.app.add_api_route("/stats", self.get_stats, methods=["GET"])
        self.app.add_api_route("/health", self.health_check, methods=["GET"])
        
        # Register lifecycle events
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)
    
    async def startup(self):
        await self.db.connect()
        
    async def shutdown(self):
        await self.db.disconnect()
        
    async def get_results(self, industry: str = None, min_score: float = None, 
                         job_id: str = None, limit: int = 100, offset: int = 0):
        return await self.service.get_results(
            industry=industry, min_score=min_score, job_id=job_id, 
            limit=limit, offset=offset
        )
        
    async def get_product(self, product_id: str):
        product = await self.service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
        
    async def get_video(self, video_id: str):
        video = await self.service.get_video(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
        
    async def get_match(self, match_id: str):
        match = await self.service.get_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return match
        
    async def get_evidence_image(self, match_id: str):
        evidence_path = await self.service.get_evidence_path(match_id)
        if not evidence_path:
            raise HTTPException(status_code=404, detail="Evidence image not found")
        # In a real implementation, this would return the image file
        # For now, we're just returning the path
        return {"evidence_path": evidence_path}
        
    async def get_stats(self):
        return await self.service.get_stats()
        
    async def health_check(self):
        # Simple health check - in a real implementation, this might check
        # database connectivity and other dependencies
        return {"status": "healthy"}