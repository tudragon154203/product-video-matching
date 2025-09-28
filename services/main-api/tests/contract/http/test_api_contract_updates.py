"""
Integration tests for API contract updates to include URL fields.
"""
from main import app
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import pytest
pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_database():
    """Mock database responses."""
    with patch('common_py.database.DatabaseManager') as mock_db:
        # Mock image data
        mock_image_data = MagicMock()
        mock_image_data.img_id = "img_001"
        mock_image_data.product_id = "prod_001"
        mock_image_data.local_path = "/app/data/images/123.jpg"
        mock_image_data.product_title = "Test Product"
        mock_image_data.updated_at = "2023-01-01T00:00:00Z"
        mock_image_data.created_at = "2023-01-01T00:00:00Z"

        # Mock frame data
        mock_frame_data = MagicMock()
        mock_frame_data.frame_id = "frame_001"
        mock_frame_data.ts = 1.5
        mock_frame_data.local_path = "/app/data/frames/456.png"
        mock_frame_data.created_at = "2023-01-01T00:00:00Z"

        # Mock video data
        mock_video_data = MagicMock()
        mock_video_data.video_id = "vid_001"
        mock_video_data.platform = "youtube"
        mock_video_data.url = "https://youtube.com/watch?v=test"
        mock_video_data.title = "Test Video"
        mock_video_data.duration_s = 120
        mock_video_data.job_id = "job_001"
        mock_video_data.created_at = "2023-01-01T00:00:00Z"

        # Mock job data
        mock_job_data = MagicMock()
        mock_job_data.job_id = "job_001"
        mock_job_data.phase = "completed"
        mock_job_data.updated_at = "2023-01-01T00:00:00Z"
        mock_job_data.percent = 100
        mock_job_data.counts = {"images": 1, "videos": 1}

        # Mock CRUD operations
        mock_crud = MagicMock()
        mock_crud.list_images_by_job.return_value = [mock_image_data]
        mock_crud.count_images_by_job.return_value = 1
        mock_crud.list_video_frames_by_video.return_value = [mock_frame_data]
        mock_crud.count_video_frames_by_video.return_value = 1
        mock_crud.get_video.return_value = mock_video_data

        mock_db.return_value = MagicMock()
        mock_db.return_value.session = MagicMock()

        yield mock_crud


class TestImageApiContract:
    """Test cases for image API contract updates."""

    def test_image_list_response_includes_url(self, client, mock_database):
        """Test that image list response includes URL field."""
        with patch('api.image_endpoints.get_gmt7_time') as mock_time:
            mock_time.return_value = "2023-01-01T07:00:00+07:00"

            with patch('services.job.job_service.JobService') as mock_job_service:
                mock_job_service.return_value.get_job_status.return_value = MagicMock(
                    job_id="job_001",
                    phase="completed",
                    updated_at="2023-01-01T00:00:00Z",
                    percent=100,
                    counts={"images": 1, "videos": 1}
                )

                response = client.get("/jobs/job_001/images")

                assert response.status_code == 200
                data = response.json()

                assert "items" in data
                assert len(data["items"]) == 1

                image_item = data["items"][0]
                assert "img_id" in image_item
                assert "product_id" in image_item
                assert "local_path" in image_item
                assert "url" in image_item  # New field
                assert "product_title" in image_item
                assert "updated_at" in image_item

                # Verify URL is correctly generated
                expected_url = "/files/images/123.jpg"
                assert image_item["url"] == expected_url

    def test_image_url_null_for_invalid_path(self, client, mock_database):
        """Test that URL is null for invalid local paths."""
        # Mock image with invalid path
        mock_image_data = MagicMock()
        mock_image_data.img_id = "img_002"
        mock_image_data.product_id = "prod_002"
        mock_image_data.local_path = "/invalid/path/image.jpg"  # Path outside data root
        mock_image_data.product_title = "Invalid Product"
        mock_image_data.updated_at = "2023-01-01T00:00:00Z"
        mock_image_data.created_at = "2023-01-01T00:00:00Z"

        mock_database.list_images_by_job.return_value = [mock_image_data]

        with patch('api.image_endpoints.get_gmt7_time') as mock_time:
            mock_time.return_value = "2023-01-01T07:00:00+07:00"

            with patch('services.job.job_service.JobService') as mock_job_service:
                mock_job_service.return_value.get_job_status.return_value = MagicMock(
                    job_id="job_002",
                    phase="completed",
                    updated_at="2023-01-01T00:00:00Z",
                    percent=100,
                    counts={"images": 1, "videos": 1}
                )

                response = client.get("/jobs/job_002/images")

                assert response.status_code == 200
                data = response.json()

                image_item = data["items"][0]
                # Should be null for invalid path
                assert image_item["url"] is None


class TestFrameApiContract:
    """Test cases for frame API contract updates."""

    def test_frame_list_response_includes_url(self, client, mock_database):
        """Test that frame list response includes URL field."""
        with patch('api.video_endpoints.get_gmt7_time') as mock_time:
            mock_time.return_value = "2023-01-01T07:00:00+07:00"

            with patch('services.job.job_service.JobService') as mock_job_service:
                mock_job_service.return_value.get_job_status.return_value = MagicMock(
                    job_id="job_001",
                    phase="completed",
                    updated_at="2023-01-01T00:00:00Z",
                    percent=100,
                    counts={"images": 1, "videos": 1}
                )

                response = client.get("/jobs/job_001/videos/vid_001/frames")

                assert response.status_code == 200
                data = response.json()

                assert "items" in data
                assert len(data["items"]) == 1

                frame_item = data["items"][0]
                assert "frame_id" in frame_item
                assert "ts" in frame_item
                assert "local_path" in frame_item
                assert "url" in frame_item  # New field
                assert "updated_at" in frame_item

                # Verify URL is correctly generated
                expected_url = "/files/frames/456.png"
                assert frame_item["url"] == expected_url

    def test_frame_url_null_for_invalid_path(self, client, mock_database):
        """Test that URL is null for invalid local paths."""
        # Mock frame with invalid path
        mock_frame_data = MagicMock()
        mock_frame_data.frame_id = "frame_002"
        mock_frame_data.ts = 2.5
        mock_frame_data.local_path = "/invalid/path/frame.png"  # Path outside data root
        mock_frame_data.created_at = "2023-01-01T00:00:00Z"

        mock_database.list_video_frames_by_video.return_value = [
            mock_frame_data]

        with patch('api.video_endpoints.get_gmt7_time') as mock_time:
            mock_time.return_value = "2023-01-01T07:00:00+07:00"

            with patch('services.job.job_service.JobService') as mock_job_service:
                mock_job_service.return_value.get_job_status.return_value = MagicMock(
                    job_id="job_001",
                    phase="completed",
                    updated_at="2023-01-01T00:00:00Z",
                    percent=100,
                    counts={"images": 1, "videos": 1}
                )

                response = client.get("/jobs/job_001/videos/vid_001/frames")

                assert response.status_code == 200
                data = response.json()

                frame_item = data["items"][0]
                # Should be null for invalid path
                assert frame_item["url"] is None


class TestResultsApiContract:
    """Test cases for results API contract updates."""

    def test_match_list_response_includes_evidence_url(self, client):
        """Test that match list response includes evidence_url field."""
        with patch('api.results_endpoints.ResultsService') as mock_service:
            # Mock match data
            mock_match = MagicMock()
            mock_match.match_id = "match_001"
            mock_match.job_id = "job_001"
            mock_match.product_id = "prod_001"
            mock_match.video_id = "vid_001"
            mock_match.best_img_id = "img_001"
            mock_match.best_frame_id = "frame_001"
            mock_match.ts = 1.5
            mock_match.score = 0.95
            mock_match.evidence_path = "/app/data/evidence/match_001.jpg"
            mock_match.created_at = "2023-01-01T00:00:00Z"
            mock_match.product_title = "Test Product"
            mock_match.video_title = "Test Video"
            mock_match.video_platform = "youtube"

            mock_service.return_value.get_results.return_value = MagicMock(
                items=[mock_match],
                total=1,
                limit=100,
                offset=0
            )

            response = client.get("/results")

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert len(data["items"]) == 1

            match_item = data["items"][0]
            assert "match_id" in match_item
            assert "job_id" in match_item
            assert "product_id" in match_item
            assert "video_id" in match_item
            assert "best_img_id" in match_item
            assert "best_frame_id" in match_item
            assert "ts" in match_item
            assert "score" in match_item
            assert "evidence_path" in match_item
            assert "evidence_url" in match_item  # New field
            assert "created_at" in match_item
            assert "product_title" in match_item
            assert "video_title" in match_item
            assert "video_platform" in match_item

            # Verify URL is correctly generated
            expected_url = "/files/evidence/match_001.jpg"
            assert match_item["evidence_url"] == expected_url

    def test_match_detail_response_includes_evidence_url(self, client):
        """Test that match detail response includes evidence_url field."""
        with patch('api.results_endpoints.ResultsService') as mock_service:
            # Mock match detail data
            mock_match = MagicMock()
            mock_match.match_id = "match_001"
            mock_match.job_id = "job_001"
            mock_match.best_img_id = "img_001"
            mock_match.best_frame_id = "frame_001"
            mock_match.ts = 1.5
            mock_match.score = 0.95
            mock_match.evidence_path = "/app/data/evidence/match_001.jpg"
            mock_match.created_at = "2023-01-01T00:00:00Z"

            # Mock product and video details
            mock_product = MagicMock()
            mock_product.product_id = "prod_001"
            mock_product.src = "ebay"
            mock_product.asin_or_itemid = "123456"
            mock_product.title = "Test Product"
            mock_product.brand = "Test Brand"
            mock_product.url = "https://ebay.com/test"
            mock_product.created_at = "2023-01-01T00:00:00Z"
            mock_product.image_count = 1

            mock_video = MagicMock()
            mock_video.video_id = "vid_001"
            mock_video.platform = "youtube"
            mock_video.url = "https://youtube.com/watch?v=test"
            mock_video.title = "Test Video"
            mock_video.duration_s = 120
            mock_video.published_at = "2023-01-01T00:00:00Z"
            mock_video.created_at = "2023-01-01T00:00:00Z"
            mock_video.frame_count = 10

            mock_match.product = mock_product
            mock_match.video = mock_video

            mock_service.return_value.get_match.return_value = mock_match

            response = client.get("/matches/match_001")

            assert response.status_code == 200
            data = response.json()

            assert "match_id" in data
            assert "job_id" in data
            assert "best_img_id" in data
            assert "best_frame_id" in data
            assert "ts" in data
            assert "score" in data
            assert "evidence_path" in data
            assert "evidence_url" in data  # New field
            assert "created_at" in data
            assert "product" in data
            assert "video" in data

            # Verify URL is correctly generated
            expected_url = "/files/evidence/match_001.jpg"
            assert data["evidence_url"] == expected_url

    def test_evidence_response_includes_url(self, client):
        """Test that evidence response includes URL field."""
        with patch('api.results_endpoints.ResultsService') as mock_service:
            mock_service.return_value.get_evidence_path.return_value = "/app/data/evidence/match_001.jpg"

            response = client.get("/evidence/match_001")

            assert response.status_code == 200
            data = response.json()

            assert "evidence_path" in data
            assert "evidence_url" in data  # New field

            # Verify URL is correctly generated
            expected_url = "/files/evidence/match_001.jpg"
            assert data["evidence_url"] == expected_url

    def test_evidence_url_null_for_invalid_path(self, client):
        """Test that evidence URL is null for invalid paths."""
        with patch('api.results_endpoints.ResultsService') as mock_service:
            mock_service.return_value.get_evidence_path.return_value = "/invalid/path/evidence.jpg"

            response = client.get("/evidence/match_001")

            assert response.status_code == 200
            data = response.json()

            assert data["evidence_path"] == "/invalid/path/evidence.jpg"
            # Should be null for invalid path
            assert data["evidence_url"] is None
