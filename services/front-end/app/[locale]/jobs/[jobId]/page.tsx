'use client';

import React, { Suspense } from 'react';
import { useTranslations } from 'next-intl';
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling';
import { JobSplitView } from '@/components/jobs/JobSplitView';
import { ProductsPanel } from '@/components/jobs/ProductsPanel';
import { VideosPanel } from '@/components/jobs/VideosPanel';


interface JobDetailsPageProps {
  params: { jobId: string; locale: string };
}

export default function JobDetailsPage({ params }: JobDetailsPageProps) {
  const { jobId } = params;
  const t = useTranslations();
  
  // Use job status polling to auto-refresh while collecting
  const { isCollecting } = useJobStatusPolling(jobId, { enabled: true });

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">{t('jobs.title')}</h1>
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