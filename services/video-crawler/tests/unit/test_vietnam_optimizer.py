"""
Unit tests for Vietnam TikTok Optimizer
"""
import pytest
from platform_crawler.tiktok.vietnam_optimizer import VietnamTikTokOptimizer, VietnamContentFilter


class TestVietnamTikTokOptimizer:
    """Test cases for VietnamTikTokOptimizer"""
    
    @pytest.fixture
    def optimizer(self):
        """Create VietnamTikTokOptimizer instance for testing"""
        return VietnamTikTokOptimizer()
    
    def test_add_vietnam_proxy(self, optimizer):
        """Test adding Vietnam proxy"""
        proxy_url = "http://user:pass@proxy.vn:8080"
        optimizer.add_vietnam_proxy(proxy_url)
        
        assert len(optimizer.vietnam_proxies) == 1
        assert optimizer.vietnam_proxies[0] == proxy_url
    
    def test_add_invalid_proxy(self, optimizer):
        """Test adding invalid proxy URL"""
        invalid_proxy = "not-a-valid-url"
        optimizer.add_vietnam_proxy(invalid_proxy)
        
        # Should not add invalid proxy
        assert len(optimizer.vietnam_proxies) == 0
    
    def test_get_next_vietnam_proxy(self, optimizer):
        """Test proxy rotation"""
        proxy1 = "http://proxy1.vn:8080"
        proxy2 = "http://proxy2.vn:8080"
        
        optimizer.add_vietnam_proxy(proxy1)
        optimizer.add_vietnam_proxy(proxy2)
        
        # Test rotation
        assert optimizer.get_next_vietnam_proxy() == proxy1
        assert optimizer.get_next_vietnam_proxy() == proxy2
        assert optimizer.get_next_vietnam_proxy() == proxy1  # Back to first
    
    def test_get_next_vietnam_proxy_empty(self, optimizer):
        """Test getting proxy when none available"""
        assert optimizer.get_next_vietnam_proxy() is None
    
    def test_enhance_search_queries_for_vietnam(self, optimizer):
        """Test query enhancement for Vietnam"""
        queries = ["product review", "tech unboxing"]
        enhanced = optimizer.enhance_search_queries_for_vietnam(queries)
        
        assert len(enhanced) > len(queries)
        assert "product review" in enhanced
        assert "tech unboxing" in enhanced
        assert "product review vietnam" in enhanced
        assert "tech unboxing việt nam" in enhanced
    
    def test_get_vietnam_hashtags_for_query(self, optimizer):
        """Test Vietnam hashtag generation"""
        hashtags = optimizer.get_vietnam_hashtags_for_query("tech")
        
        assert len(hashtags) <= 5
        assert all(len(tag) <= 50 for tag in hashtags)
        assert any("tech" in tag for tag in hashtags)
    
    def test_optimize_session_config_for_vietnam(self, optimizer):
        """Test session config optimization for Vietnam"""
        base_config = {
            "sleep_after": 1,
            "headless": False
        }
        
        optimized = optimizer.optimize_session_config_for_vietnam(base_config)
        
        assert optimized["sleep_after"] >= 5  # Increased for Vietnam
        assert optimized["headless"] is True  # Always headless
        assert "user_agent" in optimized
    
    def test_is_vietnam_peak_hour(self, optimizer):
        """Test Vietnam peak hour detection"""
        # This is time-dependent, so just test it returns a boolean
        result = optimizer.is_vietnam_peak_hour()
        assert isinstance(result, bool)
    
    def test_get_vietnam_peak_hours(self, optimizer):
        """Test getting Vietnam peak hours"""
        peak_hours = optimizer.get_vietnam_peak_hours()
        
        assert isinstance(peak_hours, list)
        assert all(0 <= hour <= 23 for hour in peak_hours)
        assert len(peak_hours) > 0


class TestVietnamContentFilter:
    """Test cases for VietnamContentFilter"""
    
    @pytest.fixture
    def content_filter(self):
        """Create VietnamContentFilter instance for testing"""
        return VietnamContentFilter()
    
    @pytest.fixture
    def test_videos(self):
        """Test videos with various Vietnam relevance levels"""
        return [
            {
                "title": "Review điện thoại mới ở Việt Nam",
                "author": "tech_vietnam",
                "view_count": 50000,
                "video_id": "vn_video_1"
            },
            {
                "title": "English tech review",
                "author": "tech_global",
                "view_count": 30000,
                "video_id": "global_video_1"
            },
            {
                "title": "Sản phẩm công nghệ tại Sài Gòn",
                "author": "saigon_tech",
                "view_count": 75000,
                "video_id": "vn_video_2"
            },
            {
                "title": "Vietnamese culture and tradition",
                "author": "vietnam_culture",
                "view_count": 25000,
                "video_id": "vn_video_3"
            }
        ]
    
    def test_is_vietnam_relevant(self, content_filter, test_videos):
        """Test Vietnam relevance detection"""
        # Vietnamese content should be relevant
        assert content_filter.is_vietnam_relevant(test_videos[0]) is True  # "Việt Nam"
        assert content_filter.is_vietnam_relevant(test_videos[2]) is True  # "Sài Gòn"
        assert content_filter.is_vietnam_relevant(test_videos[3]) is True  # "Vietnamese"
        
        # English-only content should not be relevant
        assert content_filter.is_vietnam_relevant(test_videos[1]) is False
    
    def test_score_vietnam_relevance(self, content_filter, test_videos):
        """Test Vietnam relevance scoring"""
        scores = [content_filter.score_vietnam_relevance(video) for video in test_videos]
        
        # Vietnamese content should score higher
        assert scores[0] > scores[1]  # "Việt Nam" > "English"
        assert scores[2] > scores[1]  # "Sài Gòn" > "English"
        
        # All scores should be between 0 and 1
        assert all(0 <= score <= 1 for score in scores)
    
    def test_filter_for_vietnam_market(self, content_filter, test_videos):
        """Test filtering for Vietnam market"""
        filtered = content_filter.filter_for_vietnam_market(test_videos, min_score=0.3)
        
        # Should filter out low-relevance content
        assert len(filtered) <= len(test_videos)
        
        # All filtered videos should have relevance scores
        assert all("vietnam_relevance_score" in video for video in filtered)
        
        # Should be sorted by relevance (highest first)
        scores = [video["vietnam_relevance_score"] for video in filtered]
        assert scores == sorted(scores, reverse=True)
    
    def test_enhance_video_metadata_for_vietnam(self, content_filter, test_videos):
        """Test enhancing video metadata for Vietnam"""
        enhanced = content_filter.enhance_video_metadata_for_vietnam(test_videos[0])
        
        assert "vietnam_relevance_score" in enhanced
        assert "vietnam_market_category" in enhanced
        assert "has_vietnamese_content" in enhanced
        
        # Should preserve original data
        assert enhanced["title"] == test_videos[0]["title"]
        assert enhanced["author"] == test_videos[0]["author"]
    
    def test_categorize_for_vietnam_market(self, content_filter):
        """Test categorization for Vietnam market"""
        tech_video = {"title": "Review điện thoại iPhone mới"}
        food_video = {"title": "Món phở Hà Nội ngon nhất"}
        fashion_video = {"title": "Thời trang công sở Sài Gòn"}
        general_video = {"title": "Random video content"}
        
        assert content_filter._categorize_for_vietnam_market(tech_video) == "technology"
        assert content_filter._categorize_for_vietnam_market(food_video) == "food"
        assert content_filter._categorize_for_vietnam_market(fashion_video) == "fashion"
        assert content_filter._categorize_for_vietnam_market(general_video) == "general"
    
    def test_has_vietnamese_content(self, content_filter):
        """Test Vietnamese content detection"""
        vietnamese_title = {"title": "Video về Việt Nam"}
        english_title = {"title": "English video content"}
        mixed_title = {"title": "English with tiếng Việt"}
        
        assert content_filter._has_vietnamese_content(vietnamese_title) is True
        assert content_filter._has_vietnamese_content(english_title) is False
        assert content_filter._has_vietnamese_content(mixed_title) is True