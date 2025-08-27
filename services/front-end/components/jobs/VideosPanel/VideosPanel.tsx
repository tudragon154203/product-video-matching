'use client';

import React, { useEffect, useCallback } from 'react';
import { usePaginatedListWithPreloading } from '@/lib/hooks/usePaginatedListWithPreloading';
import { videoApiService } from '@/lib/api/services/video.api';
import { VideoItem } from '@/lib/zod/video';
import { groupBy } from '@/lib/utils/groupBy';
import { formatDuration } from '@/lib/utils/formatDuration';
import { useTranslations } from 'next-intl';

import { PanelHeader } from '@/components/jobs/PanelHeader';
import { PanelSection } from '@/components/jobs/PanelSection';
import { VideoGroup } from './VideoGroup';
import { VideoItemRow } from './VideoItemRow';
import { VideosPagination } from './VideosPagination';
import { VideosSkeleton } from './VideosSkeleton';
import { VideosEmpty } from './VideosEmpty';
import { VideosError } from './VideosError';

interface VideosPanelProps {
  jobId: string;
  isCollecting?: boolean;
}

export function VideosPanel({ jobId, isCollecting = false }: VideosPanelProps) {
  const t = useTranslations('jobResults');

  // Fetch function for the hook
  const fetchVideosData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');

    return await videoApiService.getJobVideos(jobId, {
      limit,
      offset,
    });
  }, [jobId]);

  const {
    items: videos,
    total,
    isLoading,
    isNavigationLoading,
    error,
    handlePrev,
    handleNext,
    handleRetry,
    clearCache,
    fetchFunction: fetchVideos,
    loadFromCacheOrFetch,
    offset,
    limit
  } = usePaginatedListWithPreloading<VideoItem>(fetchVideosData);



  useEffect(() => {
    if (!isCollecting) {
      loadFromCacheOrFetch();
    }
  }, [loadFromCacheOrFetch, isCollecting]);

  // Auto-refetch when collecting (without showing navigation loading)
  useEffect(() => {
    if (isCollecting) {
      const interval = setInterval(() => fetchVideos(false), 5000);
      return () => clearInterval(interval);
    }
  }, [isCollecting, fetchVideos]);

  // Handle navigation changes with loading indicators
  useEffect(() => {
    if (!isCollecting && isNavigationLoading) {
      loadFromCacheOrFetch();
    }
  }, [offset, loadFromCacheOrFetch, isCollecting, isNavigationLoading]);

  // Clear cache when job changes
  useEffect(() => {
    clearCache();
  }, [jobId, clearCache]);

  const groupedVideos = groupBy(videos, v => v.platform);

  const handleRetryClick = () => {
    handleRetry();
  };

  return (
    <PanelSection data-testid="videos-panel">
      <PanelHeader
        title={t('videos.panelTitle')}
        count={total}
      />

      <div className="space-y-4 relative">
        {isNavigationLoading && videos.length > 0 && (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg">
            <div className="bg-background border rounded-lg px-4 py-2 shadow-sm flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-muted-foreground">{t('videos.loading')}</span>
            </div>
          </div>
        )}
        {isLoading && videos.length === 0 ? (
          <VideosSkeleton count={10} data-testid="videos-skeleton" />
        ) : error ? (
          <VideosError onRetry={handleRetryClick} data-testid="videos-error" />
        ) : videos.length === 0 ? (
          <VideosEmpty isCollecting={isCollecting} data-testid="videos-empty" />
        ) : (
          Object.entries(groupedVideos).map(([platform, items]) => (
            <div key={platform}>
              <VideoGroup platform={platform} count={items.length} />
              <div className="space-y-2">
                {items.map((video) => (
                  <VideoItemRow key={video.video_id} video={video} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {total > 10 && (
        <VideosPagination
          total={total}
          limit={limit}
          offset={offset}
          onPrev={handlePrev}
          onNext={handleNext}
          isLoading={isNavigationLoading}
          data-testid="videos-pagination"
        />
      )}
    </PanelSection>
  );
}