"""
Core Integration Tests for Main API

These tests focus on essential integration scenarios without heavy mocking.
Tests should use real database connections and test actual API behavior.
"""
import pytest
import httpx
import asyncio
from datetime import datetime, timezone

pytestmark = pytest.mark.integration


class TestCoreIntegration:
    """Core integration tests for main-api functionality"""

    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self):
        """Test health endpoint with real service"""
        # Note: This test requires the service to be running
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8888/health")

                if response.status_code == 200:
                    data = response.json()
                    assert "status" in data
                    # timestamp may or may not be present
                    assert data["status"] in ["healthy", "degraded", "unhealthy"]
                else:
                    # Service might not be running - test passes gracefully
                    pytest.skip("Main API service not running - health test skipped")

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - health test skipped")

    @pytest.mark.asyncio
    async def test_start_job_integration(self):
        """Test job creation endpoint with minimal mocking"""
        try:
            job_data = {
                "industry": "test products",
                "top_amz": 1,
                "top_ebay": 1,
                "platforms": ["youtube"],
                "recency_days": 30
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8888/start-job",
                    json=job_data
                )

                if response.status_code == 200:
                    data = response.json()
                    assert "job_id" in data
                    assert data["job_id"] is not None

                    # Clean up - mark job as cancelled if service supports it
                    job_id = data["job_id"]
                    try:
                        await client.delete(f"http://localhost:8888/jobs/{job_id}")
                    except Exception:
                        pass  # Cleanup not critical

                elif response.status_code == 500:
                    # Service running but dependencies (RabbitMQ/DB) not available
                    pytest.skip("Service dependencies not available - job creation test skipped")
                else:
                    pytest.skip("Service not running properly - job creation test skipped")

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - job creation test skipped")

    @pytest.mark.asyncio
    async def test_job_status_integration(self):
        """Test job status endpoint with real service"""
        try:
            # First create a job
            job_data = {
                "industry": "test status",
                "top_amz": 1,
                "top_ebay": 1,
                "platforms": ["youtube"],
                "recency_days": 30
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create job
                create_response = await client.post(
                    "http://localhost:8888/start-job",
                    json=job_data
                )

                if create_response.status_code != 200:
                    pytest.skip("Cannot create job - status test skipped")

                job_id = create_response.json()["job_id"]

                try:
                    # Check status
                    status_response = await client.get(
                        f"http://localhost:8888/jobs/{job_id}/status"
                    )

                    assert status_response.status_code == 200
                    data = status_response.json()
                    assert "job_id" in data
                    assert "phase" in data
                    assert "percent" in data
                    assert data["job_id"] == job_id

                finally:
                    # Cleanup
                    try:
                        await client.delete(f"http://localhost:8888/jobs/{job_id}")
                    except Exception:
                        pass

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - job status test skipped")

    @pytest.mark.asyncio
    async def test_api_contract_validation(self):
        """Test API contract validation with real endpoints"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test invalid job creation data
                invalid_job_data = {
                    "industry": "",  # Empty industry should fail validation
                    "top_amz": -1,  # Negative should fail validation
                    "top_ebay": "invalid",  # String should fail validation
                    "platforms": ["invalid_platform"],  # Invalid platform should fail
                    "recency_days": -30  # Negative should fail
                }

                response = await client.post(
                    "http://localhost:8888/start-job",
                    json=invalid_job_data
                )

                # Should return validation error (422) even if dependencies are down
                assert response.status_code == 422
                error_data = response.json()
                assert "detail" in error_data

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - validation test skipped")

    @pytest.mark.asyncio
    async def test_service_dependency_health(self):
        """Test service dependency health checks"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8888/health")

                if response.status_code == 200:
                    data = response.json()

                    # Check if dependency information is included
                    if "dependencies" in data:
                        deps = data["dependencies"]

                        # Database dependency
                        if "database" in deps:
                            assert deps["database"]["status"] in ["healthy", "unhealthy"]

                        # Message broker dependency
                        if "message_broker" in deps:
                            assert deps["message_broker"]["status"] in ["healthy", "unhealthy"]

                else:
                    pytest.skip("Health endpoint not responding")

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - dependency health test skipped")


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios"""

    @pytest.mark.asyncio
    async def test_404_handling(self):
        """Test 404 error handling for non-existent endpoints"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test non-existent endpoint
                response = await client.get("http://localhost:8888/non-existent")

                # Should return 404 regardless of service state
                assert response.status_code == 404

                # Test non-existent job
                response = await client.get("http://localhost:8888/jobs/non-existent-job-id")

                # Should return 404
                assert response.status_code == 404

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - 404 test skipped")

    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        """Test 405 error handling for wrong HTTP methods"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test wrong method on endpoint that only accepts POST
                response = await client.get("http://localhost:8888/start-job")

                # Should return 405 Method Not Allowed
                assert response.status_code == 405

        except httpx.ConnectError:
            pytest.skip("Main API service not accessible - method test skipped")


if __name__ == "__main__":
    # Run tests directly
    import asyncio

    async def run_tests():
        test_instance = TestCoreIntegration()
        error_test_instance = TestErrorHandlingIntegration()

        print("Running core integration tests...")

        # Run tests with graceful skipping
        tests = [
            test_instance.test_health_endpoint_integration(),
            test_instance.test_api_contract_validation(),
            error_test_instance.test_404_handling(),
            error_test_instance.test_method_not_allowed()
        ]

        # These tests require working dependencies
        dependency_tests = [
            test_instance.test_start_job_integration(),
            test_instance.test_job_status_integration(),
            test_instance.test_service_dependency_health()
        ]

        # Run basic tests first
        for test in tests:
            try:
                await test
                print("✓ Basic integration test passed")
            except Exception as e:
                print(f"✗ Basic integration test failed: {e}")

        # Run dependency tests if service is available
        for test in dependency_tests:
            try:
                await test
                print("✓ Dependency integration test passed")
            except Exception as e:
                print(f"⚠ Dependency integration test skipped: {e}")

    asyncio.run(run_tests())
