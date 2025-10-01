import os
from typing import Optional, Dict, Any

import yt_dlp
from yt_dlp.utils import DownloadError

from common_py.logging_config import configure_logging

logger = configure_logging("video-crawler:tiktok_downloader")

# Optional imports for database functionality
try:
    from libs.common_py.common_py.crud.video_frame_crud import VideoFrameCRUD
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TikTokAntiBotError(Exception):
    """Custom exception for TikTok anti-bot detection"""
    pass


class TikTokDownloader:
    """
    TikTok video downloader wrapper service using yt-dlp.
    Handles video downloads and keyframe extraction for TikTok content.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the TikTok downloader with configuration.

        Args:
            config: Configuration dictionary containing paths and settings
                   - TIKTOK_VIDEO_STORAGE_PATH: Path to store downloaded videos
                   - TIKTOK_KEYFRAME_STORAGE_PATH: Path to store extracted keyframes
                   - retries: Number of download retry attempts
                   - timeout: Download timeout in seconds
        """
        self.config = config
        self.retries = config.get('retries', 3)
        self.timeout = config.get('timeout', 30)

        # Set storage paths from config with defaults
        self.video_storage_path = config.get(
            'TIKTOK_VIDEO_STORAGE_PATH', '/tmp/videos/tiktok')
        self.keyframe_storage_path = config.get(
            'TIKTOK_KEYFRAME_STORAGE_PATH', '/tmp/keyframes/tiktok')

        # Ensure directories exist
        os.makedirs(self.video_storage_path, exist_ok=True)
        os.makedirs(self.keyframe_storage_path, exist_ok=True)

    def download_video(self, url: str, video_id: str) -> Optional[str]:
        """
        Download a TikTok video using yt-dlp.

        Args:
            url: TikTok video URL to download
            video_id: Unique identifier for the video

        Returns:
            Path to the downloaded video file, or None if download failed
        """
        import time

        # Construct output filename
        output_filename = os.path.join(self.video_storage_path, f"{video_id}.mp4")

        # yt-dlp configuration with 500MB file size limit
        ydl_opts = {
            'outtmpl': output_filename,
            'format': 'best[filesize<500M]',
            'retries': self.retries,
            'socket_timeout': self.timeout,
            'nocheckcertificate': True,
            'no_warnings': False,
            'quiet': False,
            'verbose': True,
        }

        logger.info(f"Starting download of TikTok video: {url}")

        # Retry loop with exponential backoff
        for attempt in range(self.retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Basic validation - check if file exists and has content
                if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                    # Check file size is under 500MB
                    file_size = os.path.getsize(output_filename)
                    if file_size < 500 * 1024 * 1024:  # 500MB in bytes
                        logger.info(f"Successfully downloaded video: {output_filename} ({file_size} bytes)")
                        return output_filename
                    else:
                        logger.error(f"Download failed: File exceeds 500MB limit ({file_size} bytes)")
                        # Remove oversized file
                        try:
                            os.remove(output_filename)
                        except Exception:
                            pass
                        return None
                else:
                    logger.error(f"Download failed: Output file not found or empty at {output_filename}")
                    return None

            except DownloadError as e:
                # Check for anti-bot measures
                error_str = str(e).lower()
                if any(indicator in error_str for indicator in
                       ['unable to extract', 'http error', '403', '429', 'forbidden', 'rate limit']):
                    logger.warning(f"Anti-bot measure detected for {url}: {str(e)}")
                    if attempt < self.retries - 1:
                        sleep_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, etc.
                        logger.info(f"Retrying in {sleep_time} seconds due to anti-bot detection...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All download attempts failed due to anti-bot measures for {url}")
                        raise TikTokAntiBotError(f"Anti-bot measures blocked download for {url}: {str(e)}")
                else:
                    # Other download errors
                    logger.warning(f"Download attempt {attempt + 1} failed for {url}: {str(e)}")
                    if attempt < self.retries - 1:
                        sleep_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, etc.
                        logger.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All download attempts failed for {url}")
                        return None
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.retries - 1:  # If not the last attempt
                    sleep_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, etc.
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"All download attempts failed for {url}")
                    return None

        return None

    async def extract_keyframes(self, video_path: str, video_id: str) -> Optional[str]:
        """
        Extract keyframes from a downloaded TikTok video.

        Args:
            video_path: Path to the downloaded video file
            video_id: Unique identifier for the video

        Returns:
            Path to the directory containing extracted keyframes, or None if extraction failed
        """
        logger.info(f"Starting keyframe extraction for video {video_id} from: {video_path}")

        try:
            # Create keyframes directory for this video
            keyframes_dir = os.path.join(self.keyframe_storage_path, video_id)
            os.makedirs(keyframes_dir, exist_ok=True)

            logger.debug(f"Created keyframes directory: {keyframes_dir}")

            # Import and use the length adaptive extractor
            from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor

            # Initialize extractor with keyframes directory
            extractor = LengthAdaptiveKeyframeExtractor(keyframe_root_dir=self.keyframe_storage_path)

            # Extract keyframes using the length adaptive extractor
            keyframes = await extractor.extract_keyframes(
                video_url="",  # Not needed for local file processing
                video_id=video_id,
                local_path=video_path
            )

            if keyframes:
                logger.info(f"Successfully extracted {len(keyframes)} keyframes for video {video_id}")
                for timestamp, frame_path in keyframes:
                    logger.debug(f"Extracted keyframe at timestamp {timestamp}: {frame_path}")
            else:
                logger.warning(f"No keyframes extracted for video {video_id}")

            # Always return the directory path even if no keyframes were extracted
            logger.debug(f"Returning keyframes directory: {keyframes_dir}")
            return keyframes_dir

        except Exception as e:
            logger.error(f"Error extracting keyframes from {video_path} for video {video_id}: {str(e)}")
            return None

    async def orchestrate_download_and_extract(
            self, url: str, video_id: str, video: Optional[Any] = None, db: Optional[Any] = None) -> bool:
        """
        Orchestrate the complete download and keyframe extraction process.

        Args:
            url: TikTok video URL to download
            video_id: Unique identifier for the video
            video: Optional video object to update with download results
            db: Optional database manager for persisting keyframe metadata

        Returns:
            True if both download and extraction succeeded, False otherwise
        """
        logger.info(f"Starting orchestration of download and extraction for video {video_id} from URL: {url}")

        try:
            # Step 1: Download the video
            local_path = self.download_video(url, video_id)

            if not local_path:
                logger.error(f"Download failed for video {video_id}")
                return False

            logger.info(f"Video download successful for video {video_id}: {local_path}")

            # Step 2: Extract keyframes
            keyframes_dir = await self.extract_keyframes(local_path, video_id)

            if not keyframes_dir:
                logger.error(f"Keyframe extraction failed for video {video_id}")
                return False

            logger.info(f"Keyframe extraction successful for video {video_id}: {keyframes_dir}")

            # Step 3: Update video object if provided
            if video:
                video.local_path = local_path
                video.has_download = True
                logger.debug(f"Updated video object for video {video_id} with local_path: {local_path}")
                # Note: keyframes are stored separately in the database via video_frame_crud

            # Step 4: Persist keyframe metadata to database if database connection provided
            if db and HAS_DB:
                try:
                    video_frame_crud = VideoFrameCRUD(db)

                    # Get the list of extracted keyframes
                    from keyframe_extractor.length_adaptive_extractor import LengthAdaptiveKeyframeExtractor
                    extractor = LengthAdaptiveKeyframeExtractor(keyframe_root_dir=self.keyframe_storage_path)
                    keyframes = await extractor.extract_keyframes(
                        video_url="",  # Not needed for local file processing
                        video_id=video_id,
                        local_path=local_path
                    )

                    # Persist each keyframe to the database
                    persisted_count = 0
                    for timestamp, frame_path in keyframes:
                        try:
                            video_frame_crud.create_video_frame(
                                video_id=video_id,
                                frame_path=frame_path,
                                timestamp=timestamp
                            )
                            persisted_count += 1
                            logger.debug(f"Persisted keyframe metadata for video {video_id}, timestamp {timestamp}")
                        except Exception as frame_error:
                            logger.warning(
                                f"Failed to persist keyframe metadata for video {video_id}, timestamp {timestamp}: {str(frame_error)}")

                    # Commit the session after all keyframes are created
                    if hasattr(db, 'commit'):
                        db.commit()
                        logger.info(f"Successfully committed {persisted_count} keyframes to database for video {video_id}")
                    else:
                        logger.info(f"Successfully created {persisted_count} keyframes in database for video {video_id}")

                except Exception as db_error:
                    logger.warning(f"Failed to persist keyframes to database for video {video_id}: {str(db_error)}")
                    # Try to commit if there were successful insertions
                    if hasattr(db, 'commit'):
                        try:
                            db.commit()
                        except Exception:
                            pass
                    # Don't fail the entire process if database persistence fails
            elif not HAS_DB:
                logger.info("Database persistence skipped - libs.common_py not available")

            logger.info(f"Successfully completed orchestration for video {video_id}")
            return True

        except TikTokAntiBotError as e:
            logger.error(f"Anti-bot error in orchestration for video {video_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in orchestration for video "
                              f"{video_id}: {str(e)}")
            return False
