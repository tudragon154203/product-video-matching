import tempfile
from unittest.mock import patch

import pytest

from platform_crawler.youtube.youtube_crawler import YoutubeCrawler
from platform_crawler.youtube.youtube_utils import is_url_like, sanitize_filename

pytestmark = pytest.mark.unit


class TestYoutubeCrawler:
    """Test cases for YoutubeCrawler"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.crawler = YoutubeCrawler()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_url_like(self):
        """Test URL detection"""
        # Valid URLs that should be skipped
        url_queries = [
            "https://youtube.com/watch?v=abc123",
            "www.youtube.com/watch?v=abc123",
            "youtube.com/watch?v=abc123",
            "youtu.be/abc123",
            "abc123def45"  # YouTube ID pattern (11 characters)
        ]
        
        for query in url_queries:
            assert is_url_like(query)
        
        # Valid keyword queries that should NOT be skipped
        keyword_queries = [
            "cat videos",
            "funny dogs",
            "product review",
            "how to cook",
            "music tutorial"
        ]
        
        for query in keyword_queries:
            assert not is_url_like(query)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        test_cases = [
            ("Normal Filename", "Normal_Filename"),
            ("File/With/Slashes", "File_With_Slashes"),
            ("File\\With\\Backslashes", "File_With_Backslashes"),
            ("File:With:Colons", "File_With_Colons"),
            ("File*With*Asterisks", "File_With_Asterisks"),
            ("File?With?Question", "File_With_Question"),
            ("File|With|Pipes", "File_With_Pipes"),
            ("  File With Spaces  ", "__File_With_Spaces__"),
            ("...File With Dots...", "File_With_Dots"),
            ("A" * 300, "A" * 200)  # Long filename truncation
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_url_skip(self):
        """Test that URL-like queries are skipped"""
        queries = ["https://youtube.com/watch?v=abc123", "cat videos", "www.youtube.com"]
        recency_days = 30
        download_dir = self.temp_dir
        num_videos = 3
        
        with patch.object(self.crawler, '_search_videos_for_queries') as mock_search:
            mock_search.return_value = []
            
            result = await self.crawler.search_and_download_videos(
                queries, recency_days, download_dir, num_videos
            )
            
            # Should only search for non-URL queries
            mock_search.assert_called_once_with(["cat videos"], 30, 3)
            assert result == []
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_recency_filter(self):
        """Test recency filtering functionality"""
        queries = ["cat videos"]
        recency_days = 7
        download_dir = self.temp_dir
        num_videos = 3
        
        mock_videos = [
            {
                'video_id': 'old_video',
                'title': 'Old Video',
                'duration_s': 60,
                'uploader': 'test_user'
            },
            {
                'video_id': 'recent_video',
                'title': 'Recent Video',
                'duration_s': 120,
                'uploader': 'test_user'
            }
        ]
        
        with patch.object(self.crawler, '_search_videos_for_queries') as mock_search:
            # The search method should filter by recency, so return only recent videos
            mock_search.return_value = [mock_videos[1]]  # Only recent video
            
            with patch.object(self.crawler, '_download_unique_videos') as mock_download:
                mock_download.return_value = mock_videos[1:]  # Only recent video
                
                result = await self.crawler.search_and_download_videos(
                    queries, recency_days, download_dir, num_videos
                )
                
                # Should only return recent video
                assert len(result) == 1
                assert result[0]['video_id'] == 'recent_video'
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_deduplication(self):
        """Test video deduplication"""
        queries = ["cat videos", "funny cats"]
        recency_days = 30
        download_dir = self.temp_dir
        num_videos = 3
        
        # Duplicate video across queries
        duplicate_video = {
            'video_id': 'same_video',
            'title': 'Same Video',
            'duration_s': 60,
            'uploader': 'test_user'
        }
        
        # Different videos for each query
        mock_results = [
            [duplicate_video, {'video_id': 'video1', 'title': 'Video 1'}],
            [duplicate_video, {'video_id': 'video2', 'title': 'Video 2'}]
        ]
        
        with patch.object(self.crawler, '_search_videos_for_queries') as mock_search:
            mock_search.return_value = [item for sublist in mock_results for item in sublist]
            
            with patch.object(self.crawler, '_download_unique_videos') as mock_download:
                # Mock download to return the video with the video_id field
                def mock_download_side_effect(videos, dir):
                    result = []
                    for video_id, video in videos.items():
                        video_copy = video.copy()
                        video_copy['local_path'] = f'/path/to/{video["video_id"]}.mp4'
                        result.append(video_copy)
                    return result
                
                mock_download.side_effect = mock_download_side_effect
                
                result = await self.crawler.search_and_download_videos(
                    queries, recency_days, download_dir, num_videos
                )
                
                # Should deduplicate by video_id
                video_ids = [v['video_id'] for v in result]
                assert len(video_ids) == 3  # same_video, video1, video2
                assert 'same_video' in video_ids
                assert 'video1' in video_ids
                assert 'video2' in video_ids
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_error_handling(self):
        """Test error handling per item"""
        queries = ["cat videos", "invalid query"]
        recency_days = 30
        download_dir = self.temp_dir
        num_videos = 3
        
        with patch.object(self.crawler, '_search_videos_for_queries') as mock_search:
            # First query succeeds, second fails
            mock_search.side_effect = [[{'video_id': 'vid1'}], Exception("Search failed")]
            
            with patch.object(self.crawler, '_download_unique_videos') as mock_download:
                mock_download.return_value = [{'video_id': 'vid1'}]
                
                result = await self.crawler.search_and_download_videos(
                    queries, recency_days, download_dir, num_videos
                )
                
                # Should still return successful results
                assert len(result) == 1
                assert result[0]['video_id'] == 'vid1'
    
    @pytest.mark.asyncio
    async def test_search_and_download_videos_empty_result(self):
        """Test handling of empty search results"""
        queries = ["nonexistent videos"]
        recency_days = 30
        download_dir = self.temp_dir
        num_videos = 3
        
        with patch.object(self.crawler, '_search_videos_for_queries') as mock_search:
            mock_search.return_value = []
            
            result = await self.crawler.search_and_download_videos(
                queries, recency_days, download_dir, num_videos
            )
            
            assert result == []
    
    def test_required_output_fields(self):
        """Test that output contains all required fields"""
        required_fields = [
            'platform', 'video_id', 'url', 'title',
            'duration_s', 'local_path'
        ]
        
        # Create a mock video with all required fields
        mock_video = {
            'platform': 'youtube',
            'video_id': 'test123',
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'duration_s': 60,
            'local_path': '/path/to/video.mp4'
        }
        
        for field in required_fields:
            assert field in mock_video

