"""Unit tests for TikTok data models."""
import pytest
pytestmark = pytest.mark.unit
from platform_crawler.tiktok.tiktok_models import TikTokVideo, TikTokSearchResponse


class TestTikTokVideo:
    """Unit tests for TikTokVideo model."""
    
    def test_tiktok_video_creation(self):
        """Test creating a TikTokVideo instance."""
        video = TikTokVideo(
            id="123456789",
            caption="Test video caption",
            author_handle="@testuser",
            like_count=1500,
            upload_time="2024-01-01T12:00:00Z",
            web_view_url="https://www.tiktok.com/@testuser/video/123456789"
        )
        
        assert video.id == "123456789"
        assert video.caption == "Test video caption"
        assert video.author_handle == "@testuser"
        assert video.like_count == 1500
        assert video.upload_time == "2024-01-01T12:00:00Z"
        assert video.web_view_url == "https://www.tiktok.com/@testuser/video/123456789"
    
    def test_from_api_response(self):
        """Test creating TikTokVideo from API response."""
        api_data = {
            "id": "987654321",
            "caption": "Another test video",
            "authorHandle": "@anotheruser",
            "likeCount": 2500,
            "uploadTime": "2024-02-01T15:30:00Z",
            "webViewUrl": "https://www.tiktok.com/@anotheruser/video/987654321"
        }
        
        video = TikTokVideo.from_api_response(api_data)
        
        assert video.id == "987654321"
        assert video.caption == "Another test video"
        assert video.author_handle == "@anotheruser"
        assert video.like_count == 2500
        assert video.upload_time == "2024-02-01T15:30:00Z"
        assert video.web_view_url == "https://www.tiktok.com/@anotheruser/video/987654321"
    
    def test_from_api_response_missing_fields(self):
        """Test TikTokVideo.from_api_response with missing fields."""
        api_data = {
            "id": "test_id",
            # Missing other fields
        }
        
        video = TikTokVideo.from_api_response(api_data)
        
        assert video.id == "test_id"
        assert video.caption == ""
        assert video.author_handle == ""
        assert video.like_count == 0
        assert video.upload_time == ""
        assert video.web_view_url == ""
    
    def test_to_video_metadata_dict(self):
        """Test converting TikTokVideo to video metadata dictionary."""
        video = TikTokVideo(
            id="111222333",
            caption="Metadata test video",
            author_handle="@metadatatest",
            like_count=3000,
            upload_time="2024-03-01T10:00:00Z",
            web_view_url="https://www.tiktok.com/@metadatatest/video/111222333"
        )
        
        metadata = video.to_video_metadata_dict()
        
        assert metadata["platform"] == "tiktok"
        assert metadata["url"] == "https://www.tiktok.com/@metadatatest/video/111222333"
        assert metadata["title"] == "Metadata test video"
        assert metadata["video_id"] == "111222333"
        assert metadata["author_handle"] == "@metadatatest"
        assert metadata["like_count"] == 3000
        assert metadata["upload_time"] == "2024-03-01T10:00:00Z"


class TestTikTokSearchResponse:
    """Unit tests for TikTokSearchResponse model."""
    
    def test_tiktok_search_response_creation(self):
        """Test creating a TikTokSearchResponse instance."""
        video1 = TikTokVideo(
            id="123",
            caption="Test video 1",
            author_handle="@test1",
            like_count=100,
            upload_time="2024-01-01T10:00:00Z",
            web_view_url="https://www.tiktok.com/@test1/video/123"
        )
        
        video2 = TikTokVideo(
            id="456",
            caption="Test video 2",
            author_handle="@test2",
            like_count=200,
            upload_time="2024-01-01T11:00:00Z",
            web_view_url="https://www.tiktok.com/@test2/video/456"
        )
        
        response = TikTokSearchResponse(
            results=[video1, video2],
            total_results=2,
            query="test query",
            search_metadata={"execution_time": 100}
        )
        
        assert len(response.results) == 2
        assert response.total_results == 2
        assert response.query == "test query"
        assert response.search_metadata == {"execution_time": 100}
    
    def test_from_api_response(self):
        """Test creating TikTokSearchResponse from API response."""
        api_data = {
            "results": [
                {
                    "id": "789",
                    "caption": "API response test",
                    "authorHandle": "@apitest",
                    "likeCount": 500,
                    "uploadTime": "2024-01-01T12:00:00Z",
                    "webViewUrl": "https://www.tiktok.com/@apitest/video/789"
                }
            ],
            "totalResults": 1,
            "query": "api test query",
            "search_metadata": {
                "executed_path": "/tiktok/search",
                "execution_time": 200,
                "request_hash": "test-hash-123"
            }
        }
        
        response = TikTokSearchResponse.from_api_response(api_data)
        
        assert len(response.results) == 1
        assert response.total_results == 1
        assert response.query == "api test query"
        assert response.search_metadata["executed_path"] == "/tiktok/search"
        assert response.search_metadata["execution_time"] == 200
        assert response.search_metadata["request_hash"] == "test-hash-123"
        
        # Verify the video was properly created
        video = response.results[0]
        assert video.id == "789"
        assert video.caption == "API response test"
        assert video.author_handle == "@apitest"
        assert video.like_count == 500
        assert video.upload_time == "2024-01-01T12:00:00Z"
        assert video.web_view_url == "https://www.tiktok.com/@apitest/video/789"
    
    def test_from_api_response_empty_results(self):
        """Test creating TikTokSearchResponse from API response with empty results."""
        api_data = {
            "results": [],
            "totalResults": 0,
            "query": "empty test",
            "search_metadata": {}
        }
        
        response = TikTokSearchResponse.from_api_response(api_data)
        
        assert len(response.results) == 0
        assert response.total_results == 0
        assert response.query == "empty test"
        assert response.search_metadata == {}