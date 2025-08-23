"""
Unit tests for TikTok API Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from platform_crawler.tiktok.tiktok_api_client import TikTokApiClient


class TestTikTokApiClient:
    """Test cases for TikTokApiClient"""
    
    @pytest.fixture
    def api_client(self):
        """Create TikTokApiClient instance for testing"""
        return TikTokApiClient(ms_token="test_token", proxy_url="http://test:proxy@proxy.com:8080")
    
    @pytest.mark.asyncio
    async def test_initialize_session_success(self, api_client, mock_tiktok_api):
        """Test successful session initialization"""
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            result = await api_client.initialize_session()
            
            assert result is True
            assert api_client._session_initialized is True
            assert api_client.api is not None
            mock_tiktok_api.create_sessions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_session_failure(self, api_client):
        """Test session initialization failure"""
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi') as mock_api:
            mock_api.side_effect = Exception("API initialization failed")
            
            result = await api_client.initialize_session()
            
            assert result is False
            assert api_client._session_initialized is False
    
    @pytest.mark.asyncio
    async def test_close_session(self, api_client, mock_tiktok_api):
        """Test session closure"""
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            await api_client.initialize_session()
            await api_client.close_session()
            
            assert api_client._session_initialized is False
            mock_tiktok_api.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_videos_success(self, api_client, mock_tiktok_api, mock_video_object):
        """Test successful video search"""
        # Mock hashtag search
        mock_hashtag = MagicMock()
        
        # Create an async generator for the videos
        async def mock_video_generator():
            yield mock_video_object
        
        mock_hashtag.videos = MagicMock(return_value=mock_video_generator())
        mock_tiktok_api.hashtag.return_value = mock_hashtag
        
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            await api_client.initialize_session()
            videos = await api_client.search_videos("test_query", count=1)
            
            assert len(videos) == 1
            video = videos[0]
            assert video["video_id"] == "test_video_123"
            assert video["title"] == "Test video description"
            assert video["author"] == "test_user"
            assert video["platform"] == "tiktok"
    
    @pytest.mark.asyncio
    async def test_search_videos_not_initialized(self, api_client):
        """Test search videos when session not initialized"""
        with patch.object(api_client, 'initialize_session', return_value=False):
            videos = await api_client.search_videos("test_query")
            assert videos == []
    
    @pytest.mark.asyncio
    async def test_get_video_download_url_success(self, api_client, mock_tiktok_api):
        """Test successful download URL retrieval"""
        mock_video = MagicMock()
        mock_video_data = MagicMock()
        mock_video_data.downloadAddr = "https://download.tiktok.com/video.mp4"
        
        mock_video.info = AsyncMock(return_value=mock_video_data)
        mock_tiktok_api.video.return_value = mock_video
        
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            await api_client.initialize_session()
            download_url = await api_client.get_video_download_url("test_video_id")
            
            assert download_url == "https://download.tiktok.com/video.mp4"
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_tiktok_api):
        """Test async context manager functionality"""
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            async with TikTokApiClient() as client:
                assert client._session_initialized is True
                assert client.api is not None
            
            # Session should be closed after context exit
            mock_tiktok_api.close.assert_called_once()
    
    def test_is_session_active(self, api_client, mock_tiktok_api):
        """Test session status check"""
        assert api_client.is_session_active() is False
        
        # Manually set session as initialized
        api_client._session_initialized = True
        api_client.api = mock_tiktok_api
        
        assert api_client.is_session_active() is True
    
    @pytest.mark.asyncio
    async def test_search_with_retry_on_failure(self, api_client, mock_tiktok_api):
        """Test retry mechanism on search failure"""
        # Mock hashtag to fail first two times, then succeed
        mock_hashtag = MagicMock()
        
        # Create async generators that fail then succeed
        async def failing_generator():
            raise Exception("Rate limit")
            yield  # unreachable
            
        async def empty_generator():
            return
            yield  # unreachable
        
        mock_hashtag.videos = MagicMock(side_effect=[
            failing_generator(),
            failing_generator(), 
            empty_generator()  # Success on third attempt
        ])
        
        mock_tiktok_api.hashtag.return_value = mock_hashtag
        
        with patch('platform_crawler.tiktok.tiktok_api_client.TikTokApi', return_value=mock_tiktok_api):
            await api_client.initialize_session()
            
            with patch('asyncio.sleep'):  # Speed up test
                videos = await api_client.search_videos("test_query")
            
            assert videos == []
            assert mock_hashtag.videos.call_count == 3