keyframe extraction process is using a mock implementation that creates dummy frames instead of extracting actual frames from the downloaded videos. Here's what's happening:

1. **Videos are being downloaded** : The YouTube downloader ([YoutubeDownloader](file:///O:/product-video-matching/services/video-crawler/platform_crawler/youtube/downloader/downloader.py#L14-L242)) is successfully downloading real videos to disk with the [local_path](file:///O:/product-video-matching/libs/common-py/common_py/models.py#L43-L43) field populated in the video metadata.
2. **Keyframe extraction is mocked** : The [`KeyframeExtractor.extract_keyframes`](file:///O:/product-video-matching/services/video-crawler/fetcher/keyframe_extractor.py#L18-L43) method is currently creating dummy frames instead of extracting real frames from the downloaded video files.
3. **Missing connection** : The keyframe extractor is not using the [local_path](file:///O:/product-video-matching/libs/common-py/common_py/models.py#L43-L43) information from the downloaded videos to extract actual frames.

=> Handled by Qoder
