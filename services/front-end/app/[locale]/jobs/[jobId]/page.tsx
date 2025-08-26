'use client';

import React, { Suspense, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling';
import { JobSplitView } from '@/components/jobs/JobSplitView';
import { ProductsPanel } from '@/components/jobs/ProductsPanel';
import { VideosPanel } from '@/components/jobs/VideosPanel';
import { jobApiService } from '@/lib/api/services/job.api';
import { useQuery, useQueryClient } from '@tanstack/react-query';


interface JobDetailsPageProps {
  params: { jobId: string; locale: string };
}

export default function JobDetailsPage({ params }: JobDetailsPageProps) {
  const { jobId } = params;
  const t = useTranslations();
  const queryClient = useQueryClient();
  
  // Fetch job details to get the original query
  const { data: jobData, isLoading: isJobLoading, error: jobError } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobApiService.getJob(jobId),
    staleTime: Infinity,
  });
  
  // Use job status polling to auto-refresh while collecting
  const { isCollecting } = useJobStatusPolling(jobId, { enabled: true });
  
  // Invalidate jobs list when job detail page loads to ensure sidebar is up-to-date
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['jobs-list'] });
  }, [jobId, queryClient]);

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        <div>
          {isJobLoading ? (
            <div className="h-8 bg-muted rounded animate-pulse w-1/3" />
          ) : jobError ? (
            <h1 className="text-2xl font-bold">{t('jobs.title')}</h1>
          ) : (
            <h1 className="text-2xl font-bold">
              {jobData ? jobData.query : t('jobs.title')}
            </h1>
          )}
          <p className="text-muted-foreground">
            Job ID: {jobId}
          </p>
        </div>
        
        <Suspense fallback={
          <div className="space-y-4">
            <div className="h-8 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          </div>
        }>
          <JobSplitView
            left={<ProductsPanel jobId={jobId} isCollecting={isCollecting} />}
            right={<VideosPanel jobId={jobId} isCollecting={isCollecting} />}
          />
        </Suspense>
      </div>
    </div>
  );
}