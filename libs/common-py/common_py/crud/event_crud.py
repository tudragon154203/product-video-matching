from typing import Optional
from ..database import DatabaseManager

class EventCRUD:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def record_event(self, event_id: str, event_type: str) -> None:
        """Record that an event has been processed to ensure idempotency"""
        query = """
        INSERT INTO processed_events (event_id, event_type, created_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (event_id) DO NOTHING
        """
        await self.db.execute(query, event_id, event_type)

    async def is_event_processed(self, event_id: str) -> bool:
        """Check if an event has already been processed"""
        query = "SELECT 1 FROM processed_events WHERE event_id = $1"
        result = await self.db.fetch_val(query, event_id)
        return result is not None

    async def cleanup_old_events(self, days: int = 7) -> int:
        """Clean up processed events older than specified days"""
        query = """
        DELETE FROM processed_events
        WHERE created_at < NOW() - INTERVAL '$1 days'
        RETURNING 1
        """
        result = await self.db.fetch_val(query, days)
        return result if result is not None else 0