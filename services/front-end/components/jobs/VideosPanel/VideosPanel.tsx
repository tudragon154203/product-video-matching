'use client';

import React, { useState, useEffect } from 'react';
import { usePaginatedList } from '@/lib/hooks/usePaginatedList';
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
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pagination = usePaginatedList(0, 10);

  const fetchVideos = async () => {
    if (!jobId) return;

    try {
      setIsLoading(true);
      setError(null);

      const response = await videoApiService.getJobVideos(jobId, {
        limit: pagination.limit,
        offset: pagination.offset,
      });

      setVideos(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.loadFailed'));
      setVideos([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isCollecting) {
      fetchVideos();
    }
  }, [jobId, pagination.offset, isCollecting]);

  // Auto-refetch when collecting
  useEffect(() => {
    if (isCollecting) {
      const interval = setInterval(fetchVideos, 5000);
      return () => clearInterval(interval);
    }
  }, [isCollecting, jobId]);

  const groupedVideos = groupBy(videos, v => v.platform);

  const handleRetry = () => {
    fetchVideos();
  };

  const handlePrev = () => {
    pagination.prev();
  };

  const handleNext = () => {
    pagination.next(total);
  };

  return (
    <PanelSection>
      <PanelHeader
        title={t('videos.panelTitle')}
        count={total}
      />

      <div className="space-y-4">
        {isLoading && videos.length === 0 ? (
          <VideosSkeleton count={10} />
        ) : error ? (
          <VideosError onRetry={handleRetry} />
        ) : videos.length === 0 ? (
          <VideosEmpty isCollecting={isCollecting} />
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
          limit={pagination.limit}
          offset={pagination.offset}
          onPrev={handlePrev}
          onNext={handleNext}
          isLoading={isLoading}
        />
      )}
    </PanelSection>
  );
}