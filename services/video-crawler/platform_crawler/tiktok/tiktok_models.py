"""TikTok data models for video metadata."""

from dataclasses import dataclass


@dataclass
class TikTokVideo:
    """Represents a TikTok video with metadata from search results."""

    id: str
    caption: str
    author_handle: str
    like_count: int
    upload_time: str  # ISO format timestamp
    web_view_url: str

    @classmethod
    def from_api_response(cls, video_data: dict) -> 'TikTokVideo':
        """Create a TikTokVideo from API response data."""
        return cls(
            id=video_data.get("id", ""),
            caption=video_data.get("caption", ""),
            author_handle=video_data.get("authorHandle", ""),
            like_count=video_data.get("likeCount", 0),
            upload_time=video_data.get("uploadTime", ""),
            web_view_url=video_data.get("webViewUrl", "")
        )

    def to_video_metadata_dict(self) -> dict:
        """Convert to video metadata dictionary for database storage."""
        return {
            "platform": "tiktok",
            "url": self.web_view_url,
            "title": self.caption,
            "video_id": self.id,
            "author_handle": self.author_handle,
            "like_count": self.like_count,
            "upload_time": self.upload_time
        }


@dataclass
class TikTokSearchResponse:
    """Represents a TikTok search API response."""

    results: list[TikTokVideo]
    total_results: int
    query: str
    search_metadata: dict

    @classmethod
    def from_api_response(cls, response_data: dict) -> 'TikTokSearchResponse':
        """Create a TikTokSearchResponse from API response data."""
        videos = [
            TikTokVideo.from_api_response(video_data)
            for video_data in response_data.get("results", [])
        ]

        return cls(
            results=videos,
            total_results=response_data.get("totalResults", 0),
            query=response_data.get("query", ""),
            search_metadata=response_data.get("search_metadata", {})
        )