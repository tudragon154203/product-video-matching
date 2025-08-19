import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from ..services.service import MatcherService
from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker


@pytest.fixture
def mock_db():
    """Mock database manager"""
    db = MagicMock(spec=DatabaseManager)
    db.fetch_all = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_broker():
    """Mock message broker"""
    broker = MagicMock(spec=MessageBroker)
    broker.subscribe_to_topic = AsyncMock()
    broker.publish_event = AsyncMock()
    return broker


@pytest.fixture
def matcher_service(mock_db, mock_broker):
    """Matcher service instance"""
    return MatcherService(
        mock_db,
        mock_broker,
        "/data",
        retrieval_topk=10,
        sim_deep_min=0.82,
        inliers_min=0.35,
        match_best_min=0.88,
        match_cons_min=2,
        match_accept=0.80
    )


class TestMatcherService:
    """Test cases for MatcherService"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, matcher_service):
        """Test service initialization"""
        with patch.object(matcher_service.matching_engine, 'initialize') as mock_init:
            await matcher_service.initialize()
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, matcher_service):
        """Test service cleanup"""
        with patch.object(matcher_service.matching_engine, 'cleanup') as mock_cleanup:
            await matcher_service.cleanup()
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_products(self, matcher_service, mock_db):
        """Test getting job products"""
        mock_db.fetch_all.return_value = [
            {"product_id": "product_001", "title": "Product 1"},
            {"product_id": "product_002", "title": "Product 2"}
        ]
        
        products = await matcher_service.get_job_products("job_001")
        
        # Check that the function was called with the right parameters (ignoring whitespace)
        mock_db.fetch_all.assert_called_once()
        args, kwargs = mock_db.fetch_all.call_args
        assert "products" in args[0]
        assert "WHERE p.job_id = $1" in args[0]
        assert args[1] == "job_001"
        assert len(products) == 2
        assert products[0]["product_id"] == "product_001"
    
    @pytest.mark.asyncio
    async def test_get_job_videos(self, matcher_service, mock_db):
        """Test getting job videos"""
        mock_db.fetch_all.return_value = [
            {"video_id": "video_001", "title": "Video 1"},
            {"video_id": "video_002", "title": "Video 2"}
        ]
        
        videos = await matcher_service.get_job_videos("job_001")
        
        # Check that the function was called with the right parameters (ignoring whitespace)
        mock_db.fetch_all.assert_called_once()
        args, kwargs = mock_db.fetch_all.call_args
        assert "videos" in args[0]
        assert "WHERE v.job_id = $1" in args[0]
        assert args[1] == "job_001"
        assert len(videos) == 2
        assert videos[0]["video_id"] == "video_001"
    
    @pytest.mark.asyncio
    async def test_handle_match_request_success(self, matcher_service, mock_db, mock_broker):
        """Test successful match request handling"""
        # Mock job data
        mock_db.fetch_all.side_effect = [
            # Products
            [{"product_id": "product_001", "title": "Product 1"}],
            # Videos
            [{"video_id": "video_001", "title": "Video 1"}]
        ]
        
        # Mock matching engine result
        with patch.object(matcher_service.matching_engine, 'match_product_video', return_value={
            "best_img_id": "img_001",
            "best_frame_id": "frame_001",
            "ts": 1.0,
            "score": 0.85,
            "best_pair_score": 0.88,
            "consistency": 3,
            "total_pairs": 5
        }) as mock_match:
            
            # Mock CRUD operations
            with patch.object(matcher_service, 'match_crud') as mock_crud:
                mock_crud.create_match = AsyncMock()
                
                # Test event data
                event_data = {
                    "job_id": "job_001",
                    "industry": "test",
                    "product_set_id": "set_001",
                    "video_set_id": "set_002",
                    "top_k": 10
                }
                
                await matcher_service.handle_match_request(event_data)
                
                # Verify matching was called
                mock_match.assert_called_once_with("product_001", "video_001", "job_001")
                
                # Verify match creation was called
                mock_crud.create_match.assert_called_once()
                
                # Verify event publishing
                mock_broker.publish_event.assert_called()
                
                # Check that matchings.process.completed event was published
                call_args = mock_broker.publish_event.call_args
                assert call_args[0][0] == "matchings.process.completed"
    
    @pytest.mark.asyncio
    async def test_handle_match_request_no_match(self, matcher_service, mock_db, mock_broker):
        """Test match request handling when no match is found"""
        # Mock job data
        mock_db.fetch_all.side_effect = [
            # Products
            [{"product_id": "product_001", "title": "Product 1"}],
            # Videos
            [{"video_id": "video_001", "title": "Video 1"}]
        ]
        
        # Mock matching engine to return no match
        with patch.object(matcher_service.matching_engine, 'match_product_video', return_value=None) as mock_match:
            
            event_data = {
                "job_id": "job_001",
                "industry": "test",
                "product_set_id": "set_001",
                "video_set_id": "set_002",
                "top_k": 10
            }
            
            await matcher_service.handle_match_request(event_data)
            
            # Verify matching was called
            mock_match.assert_called_once_with("product_001", "video_001", "job_001")
            
            # Verify no match was created
            with patch('services.service.MatchCRUD') as mock_crud:
                mock_crud_instance = MagicMock()
                mock_crud.return_value = mock_crud_instance
                mock_crud_instance.create_match.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_match_request_exception(self, matcher_service, mock_db, mock_broker):
        """Test match request handling when an exception occurs"""
        # Mock job data
        mock_db.fetch_all.side_effect = [
            # Products
            [{"product_id": "product_001", "title": "Product 1"}],
            # Videos
            [{"video_id": "video_001", "title": "Video 1"}]
        ]
        
        # Mock matching engine to raise exception
        with patch.object(matcher_service.matching_engine, 'match_product_video', side_effect=Exception("Matching failed")) as mock_match:
            
            event_data = {
                "job_id": "job_001",
                "industry": "test",
                "product_set_id": "set_001",
                "video_set_id": "set_002",
                "top_k": 10
            }
            
            with pytest.raises(Exception, match="Matching failed"):
                await matcher_service.handle_match_request(event_data)
            
            # Verify matching was called
            mock_match.assert_called_once_with("product_001", "video_001", "job_001")