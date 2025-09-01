import React from 'react';
import Link from 'next/link';
import { VideoItem } from '@/lib/zod/video';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { formatDuration } from '@/lib/utils/formatDuration';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { ThumbnailImage } from '@/components/common/ThumbnailImage';
import { useTranslations } from 'next-intl';

interface VideoItemRowProps {
  video: VideoItem;
  jobId: string;
  isCollecting?: boolean;
}

export function VideoItemRow({ video, jobId, isCollecting = false }: VideoItemRowProps) {
  const t = useTranslations();

  // Use the first_keyframe_url and preview_frame from the video data instead of making a separate API call
  // This eliminates the nested API call and improves performance
  // Prefer first_keyframe_url, fallback to preview_frame.url if thumbnail is not available
  const thumbnailSrc = video.first_keyframe_url || video.preview_frame?.url;

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
          src={thumbnailSrc}
          alt={video.title || 'Video thumbnail'}
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
          <span>{video.frames_count} {video.frames_count === 1 ? 'frame' : 'frames'}</span>
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
