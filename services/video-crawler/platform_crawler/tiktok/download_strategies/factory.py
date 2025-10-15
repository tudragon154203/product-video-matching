import os
from typing import Any, Dict

from .base import TikTokDownloadStrategy
from .ytdlp_strategy import YtdlpDownloadStrategy
from .scrapling_api_strategy import ScraplingApiDownloadStrategy
from .tikwm_strategy import TikwmDownloadStrategy


class TikTokDownloadStrategyFactory:
    """Factory for creating TikTok download strategies based on configuration."""

    @staticmethod
    def create_strategy(config: Dict[str, Any]) -> TikTokDownloadStrategy:
        """
        Create a TikTok download strategy based on environment variable or config.

        Args:
            config: Configuration dictionary containing strategy settings

        Returns:
            TikTokDownloadStrategy instance
        """
        strategy_type = (
            os.getenv("TIKTOK_DOWNLOAD_STRATEGY") or
            config.get("TIKTOK_DOWNLOAD_STRATEGY", "scrapling-api")
        ).lower()

        if strategy_type in ("yt-dlp", "yt_dlp"):
            return YtdlpDownloadStrategy(config)
        elif strategy_type in ("scrapling-api", "scrapling_api"):
            return ScraplingApiDownloadStrategy(config)
        elif strategy_type == "tikwm":
            return TikwmDownloadStrategy(config)
        else:
            raise ValueError(f"Unknown TikTok download strategy: {strategy_type}")


# Optional: Registry pattern for easy extension of new strategies
class TikTokDownloadStrategyRegistry:
    """Registry for TikTok download strategies to allow easy extension."""

    _strategies: Dict[str, type] = {
        "yt-dlp": YtdlpDownloadStrategy,
        "yt_dlp": YtdlpDownloadStrategy,  # Alternative underscore naming
        "scrapling-api": ScraplingApiDownloadStrategy,
        "scrapling_api": ScraplingApiDownloadStrategy,  # Alternative underscore naming
        "tikwm": TikwmDownloadStrategy,
    }

    @classmethod
    def register_strategy(cls, name: str, strategy_class: type) -> None:
        """Register a new strategy."""
        cls._strategies[name.lower()] = strategy_class

    @classmethod
    def create_strategy(cls, strategy_type: str, config: Dict[str, Any]) -> TikTokDownloadStrategy:
        """Create a strategy by name."""
        strategy_key = strategy_type.lower()
        if strategy_key not in cls._strategies:
            raise ValueError(f"Unknown TikTok download strategy: {strategy_type}")

        strategy_class = cls._strategies[strategy_key]
        return strategy_class(config)

    @classmethod
    def list_strategies(cls) -> list[str]:
        """List all registered strategies."""
        return list(cls._strategies.keys())