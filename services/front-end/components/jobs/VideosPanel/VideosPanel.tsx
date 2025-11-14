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

import type { VideoFramesFeatures } from '@/lib/zod/features';
import { Layers, Brain, Pointer } from 'lucide-react';

interface VideosPanelProps {
  jobId: string;
  isCollecting?: boolean;
  videosDone?: boolean;
  featurePhase?: boolean;
  featureSummary?: VideoFramesFeatures;
}

export function VideosPanel({ 
  jobId, 
  isCollecting = false, 
  videosDone = false,
  featurePhase = false,
  featureSummary
}: VideosPanelProps) {
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

  // Render feature phase toolbar
  const renderFeatureToolbar = () => {
    if (!featurePhase || !featureSummary) return null;

    const calcPercent = (done: number, total: number) => 
      total === 0 ? 0 : Math.round((done / total) * 100);

    return (
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-50 border-t">
        <div className="flex items-center gap-1 text-xs">
          <Layers className="h-3 w-3 text-sky-600" />
          <span className="text-muted-foreground">Segment:</span>
          <span className="font-medium">{calcPercent(featureSummary.segment.done, featureSummary.total)}%</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <Brain className="h-3 w-3 text-indigo-600" />
          <span className="text-muted-foreground">Embed:</span>
          <span className="font-medium">{calcPercent(featureSummary.embedding.done, featureSummary.total)}%</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <Pointer className="h-3 w-3 text-pink-600" />
          <span className="text-muted-foreground">Keypoints:</span>
          <span className="font-medium">{calcPercent(featureSummary.keypoints.done, featureSummary.total)}%</span>
        </div>
      </div>
    );
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
      footerChildren={renderFeatureToolbar()}
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
