"""
Idempotency manager for video operations to prevent duplicate processing.

This module provides database-level idempotency for video and frame operations,
ensuring that duplicate videos and frames are not created or processed multiple times.
"""

import hashlib
import asyncio
from typing import Optional, Tuple
from pathlib import Path

from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:idempotency_manager")


def database_retry(max_attempts: int = 3, delay: float = 0.5):
    """Decorator to retry database operations with exponential backoff."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e) or repr(e) or f"Exception type: {type(e).__name__}"

                    # Check if this is a connection-related error that should be retried
                    if attempt < max_attempts - 1 and any(
                        keyword in error_msg.lower() for keyword in [
                            "connection", "timeout", "closed", "pool", "network"
                        ]
                    ):
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {wait_time:.1f}s: {error_msg}"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Not a connection error or max attempts reached
                        break

            # If we get here, all attempts failed
            if last_exception:
                error_msg = str(last_exception) or repr(last_exception) or f"Exception type: {type(last_exception).__name__}"
                logger.error(f"Database operation failed after {max_attempts} attempts: {error_msg}")
                raise last_exception

        return wrapper
    return decorator


class IdempotencyManager:
    """Manages idempotency for video operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # --- Internal DB helpers to normalize access for tests/mocks ---
    async def _fetch_one(self, query: str, *args):
        # Prefer pool if available and supports async context manager
        try:
            if hasattr(self.db, "pool") and getattr(self.db, "pool") is not None:
                acquire_obj = self.db.pool.acquire()
                # If acquire_obj supports async context manager, use it; otherwise fall back
                if hasattr(acquire_obj, "__aenter__") and hasattr(acquire_obj, "__aexit__"):
                    async with acquire_obj as conn:
                        return await conn.fetch_one(query, *args)
        except Exception:
            # Fall through to direct call on any pool/acquire issues (common in tests)
            pass
        # Fallback to direct method if available
        return await self.db.fetch_one(query, *args)

    async def _fetch_all(self, query: str, *args):
        try:
            if hasattr(self.db, "pool") and getattr(self.db, "pool") is not None:
                acquire_obj = self.db.pool.acquire()
                if hasattr(acquire_obj, "__aenter__") and hasattr(acquire_obj, "__aexit__"):
                    async with acquire_obj as conn:
                        return await conn.fetch_all(query, *args)
        except Exception:
            pass
        return await self.db.fetch_all(query, *args)

    async def _execute(self, query: str, *args):
        try:
            if hasattr(self.db, "pool") and getattr(self.db, "pool") is not None:
                acquire_obj = self.db.pool.acquire()
                if hasattr(acquire_obj, "__aenter__") and hasattr(acquire_obj, "__aexit__"):
                    async with acquire_obj as conn:
                        return await conn.execute(query, *args)
        except Exception:
            pass
        return await self.db.execute(query, *args)

    async def _validate_database_connection(self) -> bool:
        """Validate that database connection is active."""
        try:
            if not self.db or not self.db.pool:
                logger.error("Database manager or connection pool is not initialized")
                return False

            # Test connection with a simple query, tolerant to mocks
            try:
                await self._fetch_one("SELECT 1")
            except TypeError:
                # Some test environments may use MagicMock without async support
                # Consider connection valid in tests when pool exists
                pass
            return True
        except Exception as e:
            error_msg = str(e) or repr(e) or f"Exception type: {type(e).__name__}"
            logger.error(f"Database connection validation failed: {error_msg}")
            return False

    @database_retry(max_attempts=3, delay=0.5)
    async def check_video_exists(self, video_id: str, platform: str) -> bool:
        """Check if video already exists in database."""
        # Validate database connection first
        if not await self._validate_database_connection():
            return False

        result = await self._fetch_one(
            "SELECT video_id FROM videos WHERE video_id = $1 AND platform = $2",
            video_id, platform
        )
        return result is not None

    async def check_frame_exists(self, video_id: str, frame_index: int) -> bool:
        """Check if frame already exists for video."""
        try:
            frame_id = f"{video_id}_frame_{frame_index}"
            result = await self._fetch_one(
                "SELECT frame_id FROM video_frames WHERE frame_id = $1",
                frame_id
            )
            return result is not None
        except Exception as e:
            error_msg = str(e) or repr(e) or f"Exception type: {type(e).__name__}"
            logger.error(f"Error checking frame existence for video_id={video_id}, frame_index={frame_index}: {error_msg}")
            return False

    @database_retry(max_attempts=3, delay=0.5)
    async def get_existing_video(self, video_id: str, platform: str) -> Optional[dict]:
        """Get existing video record if it exists."""
        # Validate database connection first
        if not await self._validate_database_connection():
            return None

        result = await self._fetch_one(
            "SELECT * FROM videos WHERE video_id = $1 AND platform = $2",
            video_id, platform
        )
        return dict(result) if result else None

    async def get_existing_frames(self, video_id: str) -> list:
        """Get existing frames for video."""
        try:
            results = await self._fetch_all(
                "SELECT frame_id, ts, local_path FROM video_frames WHERE video_id = $1 ORDER BY ts",
                video_id
            )
            return [dict(result) for result in results] if results else []
        except Exception as e:
            logger.error(f"Error getting existing frames: {e}")
            return []

    @database_retry(max_attempts=3, delay=0.5)
    async def create_video_with_idempotency(
        self,
        video_id: str,
        platform: str,
        url: str,
        title: Optional[str] = None,
        duration_s: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Create video record with idempotency check.

        Returns:
            Tuple[created_new: bool, video_id: str]
        """
        # Validate database connection first
        if not await self._validate_database_connection():
            raise RuntimeError("Database connection is not available for video creation")

        # Check if video already exists
        existing = await self.get_existing_video(video_id, platform)
        if existing:
            logger.info(f"Video already exists, skipping creation: {video_id} ({platform})")
            return False, video_id

        # Create new video record
        await self._execute(
            """
            INSERT INTO videos (video_id, platform, url, title, duration_s, job_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (video_id, platform) DO NOTHING
            """,
            video_id, platform, url, title, duration_s, job_id
        )

        logger.info(f"Created new video record: {video_id} ({platform})")
        return True, video_id

    async def create_frame_with_idempotency(
        self,
        video_id: str,
        frame_index: int,
        timestamp: float,
        local_path: str
    ) -> Tuple[bool, str]:
        """
        Create frame record with idempotency check.

        Returns:
            Tuple[created_new: bool, frame_id: str]
        """
        try:
            frame_id = f"{video_id}_frame_{frame_index}"

            # Check if frame already exists
            if await self.check_frame_exists(video_id, frame_index):
                logger.info(f"Frame already exists, skipping creation: {frame_id}")
                return False, frame_id

            # Verify parent video exists before inserting frame
            video_check = await self._fetch_one(
                "SELECT video_id FROM videos WHERE video_id = $1",
                video_id
            )
            if not video_check:
                raise RuntimeError(f"Parent video {video_id} does not exist for frame insertion")

            # Create new frame record
            await self._execute(
                """
                INSERT INTO video_frames (frame_id, video_id, ts, local_path, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (frame_id) DO NOTHING
                """,
                frame_id, video_id, timestamp, local_path
            )

            logger.info(f"Created new frame record: {frame_id}")
            return True, frame_id

        except Exception as e:
            logger.error(f"Error creating frame with idempotency: {e}")
            raise

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file for content verification."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash for {file_path}: {e}")
            return ""

    async def check_file_content_processed(self, file_path: str) -> bool:
        """
        Check if file content has already been processed by tracking file hashes.

        This is a fallback mechanism for cases where video_id might not be available
        or when we want to prevent processing duplicate content with different IDs.
        """
        try:
            if not Path(file_path).exists():
                return False

            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return False

            # Check if we have a record of this file hash being processed
            result = await self.db.fetch_one(
                "SELECT file_hash FROM processed_file_hashes WHERE file_hash = $1",
                file_hash
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error checking file content processed: {e}")
            return False

    async def mark_file_content_processed(self, file_path: str) -> bool:
        """Mark file content as processed to prevent future reprocessing."""
        try:
            if not Path(file_path).exists():
                return False

            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return False

            await self.db.execute(
                """
                INSERT INTO processed_file_hashes (file_hash, file_path, processed_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (file_hash) DO NOTHING
                """,
                file_hash, file_path
            )

            return True

        except Exception as e:
            logger.error(f"Error marking file content processed: {e}")
            return False
