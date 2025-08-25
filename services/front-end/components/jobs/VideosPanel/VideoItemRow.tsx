import React from 'react';
import Link from 'next/link';
import { VideoDetail } from '@/lib/zod/result';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { formatDuration } from '@/lib/utils/formatDuration';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { useTranslations } from 'next-intl';

interface VideoItemRowProps {
  video: VideoDetail;
}

export function VideoItemRow({ video }: VideoItemRowProps) {
  const t = useTranslations();
  
  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      <div className="flex-shrink-0">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="w-20 h-14 object-cover rounded-md"
            loading="lazy"
          />
        ) : (
          <div className="w-20 h-14 bg-muted rounded-md flex items-center justify-center">
            <div className="text-muted-foreground text-xs">
              No Thumbnail
            </div>
          </div>
        )}
      </div>
      
      <div className="flex-1 min-w-0">
        <Link
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium hover:text-primary truncate block"
          title={video.title}
        >
          {video.title}
        </Link>
        
        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          <span>{formatDuration(video.duration_s)}</span>
          {video.published_at && (
            <>
              <span>•</span>
              <span>{formatGMT7(video.published_at)}</span>
            </>
          )}
          {video.frame_count && (
            <>
              <span>•</span>
              <span>{video.frame_count} {video.frame_count === 1 ? 'frame' : 'frames'}</span>
            </>
          )}
        </div>
      </div>
      
      <LinkExternalIcon className="flex-shrink-0 text-muted-foreground" />
    </div>
  );
}