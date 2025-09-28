"""TikTok HTTP client for searching videos via external API."""

import asyncio

import httpx

from common_py.logging_config import configure_logging
from config_loader import config
from .tiktok_models import TikTokSearchResponse

logger = configure_logging("video-crawler:tiktok_searcher", log_level=config.LOG_LEVEL)


class TikTokSearcher:
    """HTTP client for interacting with TikTok Search API."""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.base_url = f"http://{config.TIKTOK_CRAWL_HOST}:{config.TIKTOK_CRAWL_HOST_PORT}"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(180.0),  # 3 minute timeout to accommodate slower headless crawls
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def search_tiktok(self, query: str, num_videos: int = 10) -> TikTokSearchResponse:
        """
        Search TikTok for videos matching the query using exponential backoff for error handling.
        
        Args:
            query: Search query
            num_videos: Maximum number of videos to retrieve (max 50)
            
        Returns:
            TikTokSearchResponse with video results
        """
        max_attempts = 3
        base_delay = 15.0  # Base delay in seconds for exponential backoff
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempting TikTok search for query: '{query}', num_videos: {num_videos} (attempt {attempt + 1}/{max_attempts})")
                
                # Prepare request payload
                payload = {
                    "query": query,
                    "numVideos": min(num_videos, 50),  # Cap at 50 as per API spec
                    "force_headful": False
                }
                
                # Make the API call
                response = await self.client.post(
                    f"{self.base_url}/tiktok/search",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info(f"Successfully retrieved TikTok search results for query '{query}', got {len(response_data.get('results', []))} results")
                        return TikTokSearchResponse.from_api_response(response_data)
                    except ValueError as e:  # JSON decode error
                        logger.error(f"Invalid JSON response from TikTok API for query '{query}': {response.text}")
                        raise Exception(f"Invalid JSON response from TikTok API: {e}")
                elif response.status_code == 429:
                    # Rate limited - wait before retrying with exponential backoff
                    logger.warning(f"Rate limited (429) for TikTok query '{query}' - attempt {attempt + 1}. Waiting before retry...")
                    if attempt < max_attempts - 1:  # Don't sleep after the last attempt
                        delay = base_delay * (2 ** attempt)  # Exponential backoff: 15s, 30s, 60s
                        logger.info(f"Waiting {delay:.1f}s before retrying...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise Exception(f"TikTok API rate limited after {max_attempts} attempts for query '{query}'")
                elif response.status_code == 400:
                    # Bad request - likely invalid parameters - don't retry
                    logger.error(f"Bad request to TikTok API for query '{query}': {response.text}")
                    raise Exception(f"TikTok API bad request (400) for query '{query}': {response.text}")
                else:
                    # Other error status codes
                    logger.error(f"TikTok API returned status {response.status_code} for query '{query}': {response.text}")
                    if attempt < max_attempts - 1:  # Don't retry after last attempt
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Waiting {delay:.1f}s before retrying...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise Exception(f"TikTok API error (status {response.status_code}) for query '{query}': {response.text}")
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout searching TikTok for query '{query}' - attempt {attempt + 1}")
                if attempt < max_attempts - 1:  # Don't retry after last attempt
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {delay:.1f}s before retrying...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"TikTok API timeout after {max_attempts} attempts for query '{query}'")
                    
            except httpx.RequestError as e:
                logger.error(f"Request error searching TikTok for query '{query}': {str(e)}")
                if attempt < max_attempts - 1:  # Don't retry after last attempt
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {delay:.1f}s before retrying...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"TikTok API request error after {max_attempts} attempts for query '{query}': {str(e)}")
                    
        # This line should not be reached if max_attempts logic works properly
        raise Exception(f"Failed to search TikTok after {max_attempts} attempts for query '{query}'")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
