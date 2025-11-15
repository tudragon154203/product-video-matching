import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { VideoItem } from '@/lib/zod/video';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { formatDuration } from '@/lib/utils/formatDuration';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { ThumbnailImage } from '@/components/common/ThumbnailImage';
import { videoApiService } from '@/lib/api/services/video.api';

interface VideoItemRowProps {
  video: VideoItem;
  jobId: string;
  isCollecting?: boolean;
}

export function VideoItemRow({ video, jobId, isCollecting = false }: VideoItemRowProps) {
  const t = useTranslations()
  const [thumbnailSrc, setThumbnailSrc] = useState<string | null>(
    video.first_keyframe_url || video.preview_frame?.url || null,
  );

  useEffect(() => {
    setThumbnailSrc(video.first_keyframe_url || video.preview_frame?.url || null);
  }, [video.first_keyframe_url, video.preview_frame]);

  useEffect(() => {
    let isCancelled = false;

    if (!jobId || !video.video_id || video.frames_count <= 0) {
      return undefined;
    }

    const fetchFrame = async () => {
      try {
        const response = await videoApiService.getVideoFrames(jobId, video.video_id, {
          limit: 1,
          offset: 0,
          sort_by: 'ts',
          order: 'ASC',
        });

        if (isCancelled) {
          return;
        }

        const firstFrame = response.items[0];

        if (firstFrame?.url) {
          setThumbnailSrc(firstFrame.url);
        } else if (firstFrame?.local_path) {
          setThumbnailSrc(firstFrame.local_path);
        } else {
          setThumbnailSrc(video.first_keyframe_url || video.preview_frame?.url || null);
        }
      } catch (error) {
        if (!isCancelled) {
          setThumbnailSrc(video.first_keyframe_url || video.preview_frame?.url || null);
        }
      }
    };

    fetchFrame();

    return () => {
      isCancelled = true;
    };
  }, [jobId, video.video_id, video.frames_count, video.first_keyframe_url, video.preview_frame]);

  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      {/* Video Thumbnail */}
      <Link
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-shrink-0 hover:opacity-80 transition-opacity"
      >
        <ThumbnailImage
          src={thumbnailSrc ?? undefined}
          alt={video.title || t('videos.fallbackThumbnail')}
          data-testid="video-thumbnail"
        />
      </Link>

      <div className="flex-1 min-w-0">
        <Link
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-primary hover:text-primary/80 hover:underline truncate block transition-colors"
          title={video.title}
        >
          {video.title}
        </Link>

        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          <span>{formatDuration(video.duration_s)}</span>
          <span>•</span>
          <span>{formatGMT7(video.updated_at)}</span>
          <span>•</span>
          <span>{video.frames_count} {video.frames_count === 1 ? t('videos.frame') : t('videos.frames')}</span>
        </div>
      </div>

      <Link
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
      >
        <LinkExternalIcon className="h-4 w-4" />
      </Link>
    </div>
  );
}
