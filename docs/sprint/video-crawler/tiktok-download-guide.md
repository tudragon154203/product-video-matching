# TikTok Download API Guide

This guide provides comprehensive documentation for using the `/tiktok/download` endpoint to download TikTok videos programmatically.

## Endpoint Information

- **URL**: `POST http://localhost:5680/tiktok/download`
- **Host**: localhost (local development server)
- **Port**: 5680
- **Content-Type**: `application/json`
- **Authentication**: Not required for public videos

## Quick Start

### Basic Request

```bash
curl -X POST "http://localhost:5680/tiktok/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.tiktok.com/@username/video/1234567890"
     }'
```

### With Force Headful Mode

```bash
curl -X POST "http://localhost:5680/tiktok/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.tiktok.com/@username/video/1234567890",
       "force_headful": true
     }'
```

## Request Schema

### TikTokDownloadRequest

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | Valid TikTok video URL |
| `force_headful` | boolean | No | `false` | Force headful browser mode |

### Supported URL Formats

- Standard format: `https://www.tiktok.com/@username/video/1234567890`
- Web format: `https://www.tiktok.com/tiktok/video/1234567890`
- Shortened URLs (may require redirection)

### Force Headful Mode

- **When `false`**: Uses headless mode for faster downloads
- **When `true`**: Uses visible browser mode (useful for complex scenarios)
- Test environments always use headless mode regardless of setting

## Response Schema

### Success Response (200)

```json
{
  "status": "success",
  "message": "Video download URL resolved successfully",
  "download_url": "https://example.com/video.mp4",
  "video_info": {
    "id": "1234567890",
    "title": "Sample TikTok Video",
    "author": "username",
    "duration": 45.2,
    "thumbnail_url": "https://example.com/thumbnail.jpg"
  },
  "file_size": 2567890,
  "execution_time": 12.5
}
```

### Error Response (4xx/5xx)

```json
{
  "status": "error",
  "message": "Failed to resolve download URL",
  "error_code": "INVALID_URL",
  "error_details": {
    "code": "INVALID_URL",
    "message": "Invalid TikTok video URL format"
  },
  "execution_time": 3.2
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "success" or "error" |
| `message` | string | Human-readable status message |
| `download_url` | string | Direct video download URL (success only) |
| `video_info` | object | Video metadata (success only) |
| `file_size` | integer | File size in bytes (success only) |
| `execution_time` | float | API execution time in seconds |
| `error_code` | string | Error code for debugging (error only) |
| `error_details` | object | Additional error details (error only) |

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_URL` | 400 | Invalid video URL format |
| `INVALID_VIDEO_ID` | 400 | Invalid video ID in URL |
| `NAVIGATION_FAILED` | 503 | Browser navigation failed |
| `NO_DOWNLOAD_LINK` | 404 | Could not resolve download URL |
| `DOWNLOAD_FAILED` | 500 | Download process failed |
| `INVALID_VIDEO` | 400 | Video is not accessible or private |

## Examples

### Example 1: Basic Video Download

**Request:**
```json
{
  "url": "https://www.tiktok.com/@tieentiton/video/7530618987760209170"
}
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Video download URL resolved successfully",
  "download_url": "https://tiktok-resolver.example.com/vid7530618987760209170.mp4",
  "video_info": {
    "id": "7530618987760209170",
    "title": "Amazing dance performance",
    "author": "tieentiton",
    "duration": 32.5,
    "thumbnail_url": "https://p16-sign.tiktokcdn.com/aweme_thumb/..."
  },
  "execution_time": 8.3
}
```

### Example 2: Force Headful Mode

**Request:**
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890",
  "force_headful": true
}
```

**Response:** (Same format as above, but uses visible browser)

### Example 3: Invalid URL Error

**Request:**
```json
{
  "url": "https://invalid-url.example.com/video/123"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Invalid TikTok video URL format",
  "error_code": "INVALID_URL",
  "error_details": {
    "code": "INVALID_URL",
    "message": "URL does not match TikTok domain pattern"
  },
  "execution_time": 0.5
}
```

## Integration Patterns

### Python Integration (Synchronous)

```python
import requests
import json

def download_tiktok_video(video_url: str, force_headful: bool = False) -> dict:
    """
    Download TikTok video using the API.
    
    Args:
        video_url: TikTok video URL
        force_headful: Force headful browser mode (default: False)
    
    Returns:
        dict: Download information or None on error
    """
    api_url = "http://localhost:5680/tiktok/download"
    
    payload = {
        "url": video_url,
        "force_headful": force_headful
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()  # Raise HTTP errors
        
        result = response.json()
        
        if result["status"] == "success":
            return {
                "download_url": result["download_url"],
                "video_info": result["video_info"],
                "file_size": result.get("file_size"),
                "execution_time": result.get("execution_time")
            }
        else:
            raise Exception(f"API Error: {result['message']}")
            
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Response parsing failed: {e}")
        return None
    except Exception as e:
        print(f"Failed to download video: {e}")
        return None

# Basic Usage
result = download_tiktok_video("https://www.tiktok.com/@username/video/1234567890")
if result:
    print(f"Download URL: {result['download_url']}")
    print(f"Video info: {result['video_info']}")
    print(f"File size: {result['file_size']} bytes")
else:
    print("Download failed")
```

### Python Integration (Asynchronous)

```python
import asyncio
import aiohttp
import json

async def download_tiktok_video_async(video_url: str, force_headful: bool = False) -> dict:
    """
    Download TikTok video using the API (async version).
    
    Args:
        video_url: TikTok video URL
        force_headful: Force headful browser mode (default: False)
    
    Returns:
        dict: Download information or None on error
    """
    api_url = "http://localhost:5680/tiktok/download"
    
    payload = {
        "url": video_url,
        "force_headful": force_headful
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=30) as response:
                response.raise_for_status()
                
                result = await response.json()
                
                if result["status"] == "success":
                    return {
                        "download_url": result["download_url"],
                        "video_info": result["video_info"],
                        "file_size": result.get("file_size"),
                        "execution_time": result.get("execution_time")
                    }
                else:
                    raise Exception(f"API Error: {result['message']}")
                    
    except aiohttp.ClientError as e:
        print(f"HTTP request failed: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Response parsing failed: {e}")
        return None
    except Exception as e:
        print(f"Failed to download video: {e}")
        return None

# Async Usage
async def main():
    result = await download_tiktok_video_async("https://www.tiktok.com/@username/video/1234567890")
    if result:
        print(f"Download URL: {result['download_url']}")
        print(f"Video info: {result['video_info']}")
    else:
        print("Download failed")

# Run the async example
# asyncio.run(main())
```

### Python Integration with Error Handling and Logging

```python
import requests
import json
import logging
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TikTokDownloader:
    """TikTok video downloader client."""
    
    def __init__(self, base_url: str = "http://localhost:5680"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def download_video(self, video_url: str, force_headful: bool = False, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Download a TikTok video.
        
        Args:
            video_url: TikTok video URL
            force_headful: Force headful browser mode
            timeout: Request timeout in seconds
            
        Returns:
            Download information dict or None on failure
        """
        api_url = f"{self.base_url}/tiktok/download"
        
        payload = {
            "url": video_url,
            "force_headful": force_headful
        }
        
        try:
            logger.info(f"Starting download for: {video_url}")
            
            response = self.session.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            
            if result["status"] == "success":
                logger.info("Download URL resolved successfully")
                return {
                    "download_url": result["download_url"],
                    "video_info": result["video_info"],
                    "file_size": result.get("file_size"),
                    "execution_time": result.get("execution_time"),
                    "success": True
                }
            else:
                logger.error(f"API Error: {result['message']}")
                return {
                    "error": result["message"],
                    "error_code": result.get("error_code"),
                    "success": False
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return {"error": str(e), "success": False}
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Response parsing failed: {e}")
            return {"error": "Invalid response format", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e), "success": False}

# Usage Example
if __name__ == "__main__":
    downloader = TikTokDownloader()
    
    # Single video download
    result = downloader.download_video("https://www.tiktok.com/@username/video/1234567890")
    
    if result and result.get("success"):
        print("✅ Download successful!")
        print(f"URL: {result['download_url']}")
        print(f"Info: {result['video_info']}")
    else:
        print("❌ Download failed:")
        print(f"Error: {result.get('error', 'Unknown error')}")
```

### Node.js Integration

```javascript
const axios = require('axios');

async function downloadTikTokVideo(videoUrl, forceHeadful = false) {
    const apiUrl = 'http://localhost:5680/tiktok/download';
    
    const payload = {
        url: videoUrl,
        force_headful: forceHeadful
    };
    
    try {
        const response = await axios.post(apiUrl, payload);
        const result = response.data;
        
        if (result.status === 'success') {
            return {
                downloadUrl: result.download_url,
                videoInfo: result.video_info,
                fileSize: result.file_size
            };
        } else {
            throw new Error(`API Error: ${result.message}`);
        }
    } catch (error) {
        console.error('Failed to download video:', error.response?.data?.message || error.message);
        return null;
    }
}

// Usage
(async () => {
    const result = await downloadTikTokVideo('https://www.tiktok.com/@username/video/1234567890');
    if (result) {
        console.log('Download URL:', result.downloadUrl);
        console.log('Video info:', result.videoInfo);
    }
})();
```

### cURL Integration

```bash
#!/bin/bash

# Function to download TikTok video
download_tiktok() {
    local video_url="$1"
    local force_headful="$2"
    local api_url="http://localhost:5680/tiktok/download"
    
    local payload=$(jq -n \
        --arg url "$video_url" \
        --argjson headful "${force_headful:-false}" \
        '{url: $url, force_headful: $headful}')
    
    local response=$(curl -s -X POST "$api_url" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    echo "$response" | jq .
}

# Usage examples
download_tiktok "https://www.tiktok.com/@username/video/1234567890"
download_tiktok "https://www.tiktok.com/@username/video/1234567890" true
```

## Best Practices

### 1. URL Validation
- Always validate TikTok URLs before making API calls
- Handle both standard and shortened URL formats
- Check for URL accessibility if possible

### 2. Error Handling
- Implement robust error handling for network issues and API errors
- Log error codes for debugging
- Implement retry logic for temporary failures

### 3. Performance Considerations
- Use headless mode (`force_headful: false`) for faster downloads
- Cache download URLs when appropriate
- Monitor execution times for performance optimization

### 4. Rate Limiting
- Implement client-side rate limiting to avoid overwhelming the service
- Consider adding delays between consecutive requests

### 5. Security
- Sanitize input URLs before processing
- Validate API responses before using download URLs
- Be cautious of malicious content from downloaded videos

## Troubleshooting

### Common Issues

1. **INVALID_URL Error**
   - Verify the TikTok URL format
   - Ensure the URL is accessible
   - Check for typos in the URL

2. **NAVIGATION_FAILED Error**
   - Try with `force_headful: true` for complex videos
   - Check if the video is still available
   - Verify network connectivity

3. **NO_DOWNLOAD_LINK Error**
   - The video might be private or deleted
   - Try again later if the video is newly posted
   - Check if the account exists

4. **Slow Performance**
   - Use headless mode for faster processing
   - Ensure your network has good connectivity
   - Consider server load during peak times

### Debug Tips

- Enable verbose logging to track API calls
- Monitor execution time for performance analysis
- Test with different videos to isolate issues
- Check server logs for detailed error information

## Environment Configuration

The service supports environment configuration for optimization:

### Production Configuration
```bash
# .env file
TIKTOK_DOWNLOAD_STRATEGY=chromium  # or "camoufox"
CHROMIUM_USER_DATA_DIR=/path/to/chromium/profiles
```

### Development Configuration
```bash
# .env file
TIKTOK_DOWNLOAD_STRATEGY=chromium
DEBUG=true  # Enable debug logging
```

## Support

For issues or questions:
- Check the project documentation
- Review the troubleshooting section
- Contact the development team with error details and reproduction steps
