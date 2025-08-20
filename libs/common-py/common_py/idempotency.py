"""
Idempotency utilities for preventing duplicate processing
"""
import hashlib
import json
from typing import Any, Dict, Optional
from .logging_config import configure_logging

logger = configure_logging("common-py")


class IdempotencyManager:
    """Manages idempotency keys to prevent duplicate processing"""
    
    def __init__(self, db):
        self.db = db
    
    async def initialize(self):
        """Initialize idempotency table"""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key VARCHAR(255) PRIMARY KEY,
                service VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        # Create index for cleanup
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_idempotency_expires 
            ON idempotency_keys(expires_at)
        """)
    
    def generate_key(self, service: str, data: Dict[str, Any]) -> str:
        """Generate idempotency key from service and data"""
        # Create deterministic hash from service and data
        content = f"{service}:{json.dumps(data, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def is_duplicate(self, key: str, service: str, ttl_seconds: int = 3600) -> bool:
        """Check if this is a duplicate request"""
        try:
            # Check if key exists and is not expired
            existing = await self.db.fetch_one("""
                SELECT key FROM idempotency_keys 
                WHERE key = $1 AND service = $2 AND expires_at > NOW()
            """, key, service)
            
            if existing:
                logger.info("Duplicate request detected", key=key, service=service)
                return True
            
            # Store the key
            await self.db.execute("""
                INSERT INTO idempotency_keys (key, service, expires_at)
                VALUES ($1, $2, NOW() + INTERVAL '%s seconds')
                ON CONFLICT (key) DO NOTHING
            """ % ttl_seconds, key, service)
            
            return False
            
        except Exception as e:
            logger.error("Failed to check idempotency", key=key, service=service, error=str(e))
            # On error, assume not duplicate to avoid blocking processing
            return False
    
    async def cleanup_expired(self):
        """Clean up expired idempotency keys"""
        try:
            deleted_count = await self.db.execute("""
                DELETE FROM idempotency_keys WHERE expires_at < NOW()
            """)
            
            if deleted_count:
                logger.info("Cleaned up expired idempotency keys", count=deleted_count)
                
        except Exception as e:
            logger.error("Failed to cleanup idempotency keys", error=str(e))