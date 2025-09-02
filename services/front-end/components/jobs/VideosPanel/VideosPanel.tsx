'use client';

import React, { useCallback } from 'react';
import { videoApiService } from '@/lib/api/services/video.api';
import { VideoItem } from '@/lib/zod/video';
import { groupBy } from '@/lib/utils/groupBy';
import { formatDuration } from '@/lib/utils/formatDuration';
import { useTranslations } from 'next-intl';
import { queryKeys } from '@/lib/api/hooks';
import { CommonPanelLayout, CommonPagination, usePanelData } from '@/components/CommonPanel';
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList';

import { VideoGroup } from './VideoGroup';
import { VideoItemRow } from './VideoItemRow';
import { VideosSkeleton } from './VideosSkeleton';
import { VideosEmpty } from './VideosEmpty';
import { VideosError } from './VideosError';
import { Badge } from '@/components/ui/badge';

interface VideosPanelProps {
  jobId: string;
  isCollecting?: boolean;
  videosDone?: boolean;
}

export function VideosPanel({ jobId, isCollecting = false, videosDone = false }: VideosPanelProps) {
  const t = useTranslations('jobResults');

  // Animation hook for smooth list transitions
  const { parentRef: videosListRef } = useAutoAnimateList<HTMLDivElement>();

  // Fetch function for TanStack Query
  const fetchVideosData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');

    return await videoApiService.getJobVideos(jobId, {
      limit,
      offset,
      sort_by: 'platform',
      order: 'ASC'
    });
  }, [jobId]);

  const {
    items: videos = [],
    total,
    isLoading,
    isNavigationLoading,
    isError,
    error,
    handlePrev,
    handleNext,
    handleRetry,
    isPlaceholderData,
    offset,
    limit
  } = usePanelData<VideoItem>({
    jobId,
    isCollecting,
    limit: 10,
    fetchFunction: fetchVideosData,
    queryKey: (offset, limit) => [...queryKeys.videos.byJob(jobId, { offset, limit })],
    enabled: !!jobId,
  });

  const groupedVideos = groupBy(videos, v => v.platform);

  const handleRetryClick = () => {
    handleRetry();
  };

  return (
    <CommonPanelLayout
      title={t('videos.panelTitle')}
      count={total}
      headerChildren={
        videosDone ? (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs text-green-600">✔ Videos done</Badge>
          </div>
        ) : null
      }
      isPlaceholderData={isPlaceholderData}
      isNavigationLoading={isNavigationLoading}
      isLoading={isLoading}
      isError={isError}
      isEmpty={videos.length === 0}
      error={error}
      onRetry={handleRetryClick}
      testId="videos-panel"
      skeletonComponent={<VideosSkeleton count={10} data-testid="videos-skeleton" />}
      emptyComponent={<VideosEmpty isCollecting={isCollecting} data-testid="videos-empty" />}
      errorComponent={<VideosError onRetry={handleRetryClick} data-testid="videos-error" />}
    >
      <div ref={videosListRef}>
        {Object.entries(groupedVideos).map(([platform, items]) => (
          <div key={platform}>
            <VideoGroup platform={platform} count={items.length} />
            <div className="space-y-2">
              {items.map((video) => (
                <VideoItemRow key={video.video_id} video={video} jobId={jobId} isCollecting={isCollecting} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {total > 10 && (
        <CommonPagination
          total={total}
          limit={limit}
          offset={offset}
          onPrev={handlePrev}
          onNext={handleNext}
          isLoading={isNavigationLoading}
          testId="videos-pagination"
        />
      )}
    </CommonPanelLayout>
  );
}
