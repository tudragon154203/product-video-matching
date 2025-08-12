import asyncpg
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async PostgreSQL database manager using asyncpg"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=1,
            max_size=10
        )
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch single value"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)