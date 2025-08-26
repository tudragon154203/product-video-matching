import asyncio
import time
from typing import Dict, Any
from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler")

class RetryHandler:
    """Handles retry logic for YouTube video downloads"""
    
    @staticmethod
    async def handle_retry(video: Dict[str, Any], title: str, attempt: int, max_retries: int, error_msg: str) -> bool:
        """
        Handle retry logic based on error type
        
        Args:
            video: Video metadata
            title: Video title for logging
            attempt: Current attempt number
            max_retries: Maximum number of retries
            error_msg: Error message from the failed attempt
            
        Returns:
            bool: True if should retry, False otherwise
        """
        if attempt >= max_retries - 1:
            return False
            
        # Check error type and handle accordingly
        if "HTTP Error 403" in error_msg or "403" in error_msg:
            logger.warning(f"[DOWNLOAD-403] Video: {title} | HTTP 403 Forbidden error detected")
            wait_time = 10 * (attempt + 1)  # Increase wait time for 403 errors
            logger.info(f"[DOWNLOAD-403-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 403 error")
            await asyncio.sleep(wait_time)
            return True
            
        elif "HTTP Error 429" in error_msg or "429" in error_msg or "Too Many Requests" in error_msg:
            logger.warning(f"[DOWNLOAD-429] Video: {title} | HTTP 429 Too Many Requests error detected")
            wait_time = 15 * (attempt + 1)  # Even longer wait for 429 errors
            logger.info(f"[DOWNLOAD-429-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} due to 429 error")
            await asyncio.sleep(wait_time)
            return True
            
        elif "empty" in error_msg.lower() or "empty file" in error_msg.lower():
            logger.warning(f"[DOWNLOAD-EMPTY-ERROR] Video: {title} | Empty file error detected")
            wait_time = 5 * (attempt + 1)
            logger.info(f"[DOWNLOAD-EMPTY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} with different format")
            await asyncio.sleep(wait_time)
            return True
            
        elif "proxy" in error_msg.lower() or "connection" in error_msg.lower():
            logger.warning(f"[DOWNLOAD-PROXY-ERROR] Video: {title} | Proxy/connection error detected")
            wait_time = 5 * (attempt + 1)
            logger.info(f"[DOWNLOAD-PROXY-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2} without proxy")
            await asyncio.sleep(wait_time)
            return True
            
        else:
            # Generic retry with exponential backoff
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"[DOWNLOAD-RETRY] Video: {title} | Waiting {wait_time}s before retry {attempt+2}")
            await asyncio.sleep(wait_time)
            return True