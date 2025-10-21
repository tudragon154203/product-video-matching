"""
Simple setup test to debug integration test issues
"""
import pytest
import asyncio
from typing import Dict, Any

from support.feature_extraction_fixtures import TestFeatureExtractionPhase as TestFeatureExtractionPhaseFixtures

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.feature_extraction,
    pytest.mark.timeout(30)  # Short timeout for debugging
]

class TestSimpleSetup(TestFeatureExtractionPhaseFixtures):
    """Simple test to debug setup issues"""

    async def test_simple_database_setup(
        self,
        feature_extraction_test_environment: Dict[str, Any]
    ):
        """Simple test: just setup database and verify"""
        env = feature_extraction_test_environment
        db_manager = env["db_manager"]

        # Build test data
        job_id = "test_simple_setup_001"
        product_records = [
            {
                "product_id": f"{job_id}_product_001",
                "img_id": f"{job_id}_img_001", 
                "local_path": "/app/data/tests/products/ready/prod_001.jpg",
                "src": "amazon",
                "asin_or_itemid": f"{job_id}_ASIN_001",
                "marketplace": "us",
            }
        ]

        # Setup database state
        await self._setup_product_database_state(db_manager, job_id, product_records)
        
        print(f"Database setup completed for job {job_id}")
        
        # Verify records exist
        result = await db_manager.fetch_all(
            "SELECT product_id, job_id FROM products WHERE job_id = $1",
            job_id
        )
        assert len(result) > 0, "No products found in database"
        print(f"Found {len(result)} products in database")

    async def _setup_product_database_state(self, db_manager, job_id: str, product_records):
        """Setup database state for product tests"""
        # Create job record
        await db_manager.execute(
            """
            INSERT INTO jobs (job_id, industry, phase, created_at, updated_at)
            VALUES ($1, 'ergonomic pillows', 'feature_extraction', NOW(), NOW())
            ON CONFLICT (job_id) DO NOTHING;
            """,
            job_id
        )

        # Insert product records
        for record in product_records:
            await db_manager.execute(
                """
                INSERT INTO products (product_id, job_id, src, asin_or_itemid, marketplace, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (product_id) DO NOTHING;
                """,
                record["product_id"],
                job_id,
                record["src"],
                record["asin_or_itemid"],
                record["marketplace"],
            )

            await db_manager.execute(
                """
                INSERT INTO product_images (img_id, product_id, local_path, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (img_id) DO NOTHING;
                """,
                record["img_id"],
                record["product_id"],
                record["local_path"],
            )
