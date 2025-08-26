import React from 'react';
import Link from 'next/link';
import { VideoItem } from '@/lib/zod/video';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { formatDuration } from '@/lib/utils/formatDuration';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { useTranslations } from 'next-intl';

interface VideoItemRowProps {
  video: VideoItem;
}

export function VideoItemRow({ video }: VideoItemRowProps) {
  const t = useTranslations();
  
  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      <div className="flex-shrink-0">
        {/* Thumbnails are not available in VideoItem, so we'll remove this part */}
        <Link
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-20 h-14 bg-muted rounded-md flex items-center justify-center hover:bg-muted/80 transition-colors"
        >
          <div className="text-muted-foreground text-xs">
            Video
          </div>
        </Link>
      </div>
      
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