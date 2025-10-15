"""
Database cleanup utilities for collection phase integration tests.
Extends existing patterns to handle product tables, video tables, and event ledgers.
"""
from typing import List, Optional, Dict, Any
from common_py.database import DatabaseManager
from common_py.logging_config import configure_logging

logger = configure_logging("test-utils:db-cleanup")


class CollectionPhaseCleanup:
    """
    Database cleanup utilities for collection phase testing.
    Provides comprehensive cleanup for all related tables and test isolation.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._cleanup_order = [
            # Child tables first (to avoid foreign key constraints)
            "video_frames",
            "product_images", 
            "matches",
            
            # Parent tables
            "videos",
            "products",
            
            # Job and event tables
            "jobs",
            "event_ledger"
        ]
        
        self._table_constraints = {
            "video_frames": ["video_id"],
            "product_images": ["product_id"],
            "matches": ["job_id"],
            "videos": ["job_id"],
            "products": ["job_id"],
            "jobs": ["job_id"],
            "event_ledger": ["job_id"]
        }
    
    async def cleanup_test_data(self, job_id_pattern: str = "test_%"):
        """
        Clean up all test data matching the job ID pattern.
        
        Args:
            job_id_pattern: Pattern to match test job IDs (default: "test_%")
        """
        logger.info("Starting collection phase cleanup", job_id_pattern=job_id_pattern)
        
        try:
            # Clean up in dependency order
            for table in self._cleanup_order:
                await self._cleanup_table(table, job_id_pattern)
            
            logger.info("Collection phase cleanup completed", job_id_pattern=job_id_pattern)
            
        except Exception as e:
            logger.error("Collection phase cleanup failed", error=str(e))
            raise
    
    async def cleanup_table(self, table_name: str, job_id_pattern: str = "test_%"):
        """
        Clean up a specific table matching the job ID pattern.
        
        Args:
            table_name: Name of the table to clean
            job_id_pattern: Pattern to match test job IDs
        """
        await self._cleanup_table(table_name, job_id_pattern)
    
    async def _cleanup_table(self, table_name: str, job_id_pattern: str):
        """Clean up a specific table with proper constraint handling"""
        constraint_column = self._table_constraints.get(table_name)
        
        if not constraint_column:
            logger.warning("Unknown table for cleanup", table=table_name)
            return
        
        # For tables with direct job_id constraint
        if constraint_column == "job_id":
            query = f"DELETE FROM {table_name} WHERE {constraint_column} LIKE $1"
            await self.db_manager.execute(query, job_id_pattern)
            
        # For tables with foreign key constraints
        elif constraint_column in ["video_id", "product_id"]:
            # Use subquery to find related records
            if constraint_column == "video_id":
                query = f"""
                    DELETE FROM {table_name} 
                    WHERE {constraint_column} IN (
                        SELECT {constraint_column} FROM videos 
                        WHERE job_id LIKE $1
                    )
                """
            elif constraint_column == "product_id":
                query = f"""
                    DELETE FROM {table_name} 
                    WHERE {constraint_column} IN (
                        SELECT {constraint_column} FROM products 
                        WHERE job_id LIKE $1
                    )
                """
            
            await self.db_manager.execute(query, job_id_pattern)
        
        logger.debug("Cleaned table", table=table_name, pattern=job_id_pattern)
    
    async def cleanup_specific_job(self, job_id: str):
        """
        Clean up data for a specific job ID.
        
        Args:
            job_id: Specific job ID to clean up
        """
        logger.info("Cleaning up specific job", job_id=job_id)
        
        try:
            # Clean up in dependency order
            for table in self._cleanup_order:
                await self._cleanup_specific_job_table(table, job_id)
            
            logger.info("Specific job cleanup completed", job_id=job_id)
            
        except Exception as e:
            logger.error("Specific job cleanup failed", job_id=job_id, error=str(e))
            raise
    
    async def _cleanup_specific_job_table(self, table_name: str, job_id: str):
        """Clean up a specific table for a specific job ID"""
        constraint_column = self._table_constraints.get(table_name)
        
        if not constraint_column:
            return
        
        # For tables with direct job_id constraint
        if constraint_column == "job_id":
            query = f"DELETE FROM {table_name} WHERE {constraint_column} = $1"
            await self.db_manager.execute(query, job_id)
            
        # For tables with foreign key constraints
        elif constraint_column in ["video_id", "product_id"]:
            # Use subquery to find related records
            if constraint_column == "video_id":
                query = f"""
                    DELETE FROM {table_name} 
                    WHERE {constraint_column} IN (
                        SELECT {constraint_column} FROM videos 
                        WHERE job_id = $1
                    )
                """
            elif constraint_column == "product_id":
                query = f"""
                    DELETE FROM {table_name} 
                    WHERE {constraint_column} IN (
                        SELECT {constraint_column} FROM products 
                        WHERE job_id = $1
                    )
                """
            
            await self.db_manager.execute(query, job_id)
        
        logger.debug("Cleaned table for specific job", table=table_name, job_id=job_id)
    
    async def truncate_tables(self, table_names: Optional[List[str]] = None):
        """
        Truncate specified tables (for complete reset).
        
        Args:
            table_names: List of table names to truncate (default: all cleanup tables)
        """
        if table_names is None:
            table_names = self._cleanup_order
        
        logger.info("Truncating tables", tables=table_names)
        
        try:
            # Disable foreign key constraints temporarily
            await self.db_manager.execute("SET session_replication_role = replica")
            
            # Truncate tables
            for table in table_names:
                if table in self._cleanup_order:
                    await self.db_manager.execute(f"TRUNCATE TABLE {table} CASCADE")
                    logger.debug("Truncated table", table=table)
            
            # Re-enable foreign key constraints
            await self.db_manager.execute("SET session_replication_role = DEFAULT")
            
            logger.info("Table truncation completed", tables=table_names)
            
        except Exception as e:
            logger.error("Table truncation failed", error=str(e))
            # Ensure constraints are re-enabled
            try:
                await self.db_manager.execute("SET session_replication_role = DEFAULT")
            except:
                pass
            raise
    
    async def get_test_data_summary(self, job_id_pattern: str = "test_%") -> Dict[str, int]:
        """
        Get a summary of test data in the database.
        
        Args:
            job_id_pattern: Pattern to match test job IDs
            
        Returns:
            Dictionary with table names and record counts
        """
        summary = {}
        
        for table in self._cleanup_order:
            constraint_column = self._table_constraints.get(table)
            
            if not constraint_column:
                continue
            
            try:
                # For tables with direct job_id constraint
                if constraint_column == "job_id":
                    query = f"SELECT COUNT(*) FROM {table} WHERE {constraint_column} LIKE $1"
                    count = await self.db_manager.fetch_val(query, job_id_pattern)
                    summary[table] = count
                    
                # For tables with foreign key constraints
                elif constraint_column in ["video_id", "product_id"]:
                    # Use subquery to count related records
                    if constraint_column == "video_id":
                        query = f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE {constraint_column} IN (
                                SELECT {constraint_column} FROM videos 
                                WHERE job_id LIKE $1
                            )
                        """
                    elif constraint_column == "product_id":
                        query = f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE {constraint_column} IN (
                                SELECT {constraint_column} FROM products 
                                WHERE job_id LIKE $1
                            )
                        """
                    
                    count = await self.db_manager.fetch_val(query, job_id_pattern)
                    summary[table] = count
                    
            except Exception as e:
                logger.warning("Failed to count records in table", table=table, error=str(e))
                summary[table] = -1
        
        return summary
    
    async def verify_cleanup(self, job_id_pattern: str = "test_%") -> bool:
        """
        Verify that cleanup was successful by checking for remaining test data.
        
        Args:
            job_id_pattern: Pattern to match test job IDs
            
        Returns:
            True if cleanup was successful (no test data remaining)
        """
        summary = await self.get_test_data_summary(job_id_pattern)
        
        remaining_data = {table: count for table, count in summary.items() if count > 0}
        
        if remaining_data:
            logger.warning(
                "Test data remains after cleanup",
                remaining_data=remaining_data
            )
            return False
        
        logger.info("Cleanup verification successful", job_id_pattern=job_id_pattern)
        return True


class DatabaseStateValidator:
    """
    Utilities for validating database state during integration tests.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def assert_job_exists(self, job_id: str):
        """Assert that a job exists in the database"""
        query = "SELECT COUNT(*) FROM jobs WHERE job_id = $1"
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count == 0:
            raise AssertionError(f"Job {job_id} not found in database")
    
    async def assert_job_not_exists(self, job_id: str):
        """Assert that a job does not exist in the database"""
        query = "SELECT COUNT(*) FROM jobs WHERE job_id = $1"
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count > 0:
            raise AssertionError(f"Job {job_id} found in database but should not exist")
    
    async def assert_products_collected(self, job_id: str, min_count: int = 1):
        """Assert that products were collected for a job"""
        query = "SELECT COUNT(*) FROM products WHERE job_id = $1"
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count < min_count:
            raise AssertionError(
                f"Expected at least {min_count} products for job {job_id}, found {count}"
            )
    
    async def assert_videos_collected(self, job_id: str, min_count: int = 1):
        """Assert that videos were collected for a job"""
        query = "SELECT COUNT(*) FROM videos WHERE job_id = $1"
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count < min_count:
            raise AssertionError(
                f"Expected at least {min_count} videos for job {job_id}, found {count}"
            )
    
    async def assert_video_frames_exist(self, job_id: str, min_count: int = 1):
        """Assert that video frames were processed for a job"""
        query = """
            SELECT COUNT(*) FROM video_frames vf
            JOIN videos v ON vf.video_id = v.video_id
            WHERE v.job_id = $1
        """
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count < min_count:
            raise AssertionError(
                f"Expected at least {min_count} video frames for job {job_id}, found {count}"
            )
    
    async def assert_product_images_exist(self, job_id: str, min_count: int = 1):
        """Assert that product images were processed for a job"""
        query = """
            SELECT COUNT(*) FROM product_images pi
            JOIN products p ON pi.product_id = p.product_id
            WHERE p.job_id = $1
        """
        count = await self.db_manager.fetch_val(query, job_id)
        
        if count < min_count:
            raise AssertionError(
                f"Expected at least {min_count} product images for job {job_id}, found {count}"
            )
    
    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Get the status of a job"""
        query = "SELECT status FROM jobs WHERE job_id = $1"
        return await self.db_manager.fetch_val(query, job_id)
    
    async def assert_job_status(self, job_id: str, expected_status: str):
        """Assert that a job has a specific status"""
        actual_status = await self.get_job_status(job_id)
        
        if actual_status != expected_status:
            raise AssertionError(
                f"Expected job {job_id} to have status {expected_status}, got {actual_status}"
            )
    
    async def get_collection_summary(self, job_id: str) -> Dict[str, int]:
        """Get a summary of collection results for a job"""
        summary = {}
        
        # Products count
        summary["products"] = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM products WHERE job_id = $1", job_id
        )
        
        # Videos count
        summary["videos"] = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM videos WHERE job_id = $1", job_id
        )
        
        # Video frames count
        summary["video_frames"] = await self.db_manager.fetch_val(
            """
                SELECT COUNT(*) FROM video_frames vf
                JOIN videos v ON vf.video_id = v.video_id
                WHERE v.job_id = $1
            """, job_id
        )
        
        # Product images count
        summary["product_images"] = await self.db_manager.fetch_val(
            """
                SELECT COUNT(*) FROM product_images pi
                JOIN products p ON pi.product_id = p.product_id
                WHERE p.job_id = $1
            """, job_id
        )
        
        # Matches count
        summary["matches"] = await self.db_manager.fetch_val(
            "SELECT COUNT(*) FROM matches WHERE job_id = $1", job_id
        )
        
        return summary