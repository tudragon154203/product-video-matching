'use client';

import React, { Suspense, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling';
import { JobSplitView } from '@/components/jobs/JobSplitView';
import { ProductsPanel } from '@/components/jobs/ProductsPanel';
import { VideosPanel } from '@/components/jobs/VideosPanel';
import { JobStatusHeader } from '@/components/jobs/JobStatusHeader';
import { FeatureExtractionBanner } from '@/components/jobs/FeatureExtractionBanner';
import { FeatureExtractionPanel } from '@/components/jobs/FeatureExtractionPanel';
import { MatchingBanner } from '@/components/jobs/MatchingPanel';
import { MatchingPanel } from '@/components/jobs/MatchingPanel';
import { CollectionSummary } from '@/components/jobs/CollectionSummary';
import { JobActionButtons } from '@/components/jobs/JobActionButtons';
import { jobApiService } from '@/lib/api/services/job.api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useFeaturesSummary, useMatchingSummary } from '@/lib/api/hooks';
import type { Phase } from '@/lib/zod/job';


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
  const { phase, percent, isCollecting, collection, counts } = useJobStatusPolling(jobId, { enabled: true });
  
  // Fetch feature summary when in feature extraction, matching, or evidence phase
  const isFeaturePhase = phase === 'feature_extraction' || phase === 'matching' || phase === 'evidence';
  const { 
    data: featureSummary, 
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    refetch: refetchSummary
  } = useFeaturesSummary(
    jobId, 
    isFeaturePhase,
    phase === 'feature_extraction' ? 5000 : false
  );
  
  // Fetch matching summary when in matching, evidence, or completed phase
  const isMatchingPhase = phase === 'matching' || phase === 'evidence' || phase === 'completed';
  const {
    data: matchingSummary,
    isLoading: isMatchingLoading,
    isError: isMatchingError,
    refetch: refetchMatching
  } = useMatchingSummary(
    jobId,
    isMatchingPhase,
    phase === 'matching' || phase === 'evidence' ? 4000 : false
  );
  
  // Invalidate jobs list when job detail page loads to ensure sidebar is up-to-date
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['jobs-list'] });
  }, [jobId, queryClient]);

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        <div className="flex justify-between items-start">
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
          {phase && <JobActionButtons jobId={jobId} phase={phase as Phase} />}
        </div>
        
        <Suspense fallback={
          <div className="space-y-4">
            <div className="h-8 bg-muted rounded animate-pulse" />
            <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          </div>
        }>
          <div className="space-y-6">
            {/* Feature Extraction Banner */}
            {phase === 'feature_extraction' && (
              <FeatureExtractionBanner 
                percent={percent} 
                counts={counts}
              />
            )}
            
            {/* Matching Banner */}
            {(phase === 'matching' || phase === 'evidence') && (
              <MatchingBanner 
                percent={percent}
                matchesFound={matchingSummary?.matches_found}
              />
            )}
            
            <JobStatusHeader jobId={jobId} isCollecting={isCollecting} />
            
            {/* Matching Panel - appears during matching and evidence phases */}
            {(phase === 'matching' || phase === 'evidence' || phase === 'completed') && (
              <MatchingPanel
                jobId={jobId}
                summary={matchingSummary}
                isLoading={isMatchingLoading}
                isError={isMatchingError}
                onRetry={refetchMatching}
                isActive={phase === 'matching' || phase === 'evidence'}
              />
            )}
            
            {/* Feature Extraction Progress Board - stays visible after phase advances */}
            {(phase === 'feature_extraction' || phase === 'matching' || phase === 'evidence') && (
              <FeatureExtractionPanel
                jobId={jobId}
                summary={featureSummary}
                isLoading={isSummaryLoading}
                isError={isSummaryError}
                onRetry={refetchSummary}
                isActive={phase === 'feature_extraction'}
              />
            )}
            
            {/* Show panels normally during collection, or inside accordion during feature extraction */}
            {phase === 'collection' ? (
              <JobSplitView
                left={
                  <ProductsPanel
                    jobId={jobId}
                    isCollecting={isCollecting}
                    productsDone={!!collection?.products_done}
                    featurePhase={false}
                  />
                }
                right={
                  <VideosPanel
                    jobId={jobId}
                    isCollecting={isCollecting}
                    videosDone={!!collection?.videos_done}
                    featurePhase={false}
                  />
                }
              />
            ) : (
              <CollectionSummary
                phase={phase || 'unknown'}
                collection={collection}
                counts={counts}
              >
                <JobSplitView
                  left={
                    <ProductsPanel
                      jobId={jobId}
                      isCollecting={false}
                      productsDone={!!collection?.products_done}
                      featurePhase={phase === 'feature_extraction'}
                      featureSummary={featureSummary?.product_images}
                    />
                  }
                  right={
                    <VideosPanel
                      jobId={jobId}
                      isCollecting={false}
                      videosDone={!!collection?.videos_done}
                      featurePhase={phase === 'feature_extraction'}
                      featureSummary={featureSummary?.video_frames}
                    />
                  }
                />
              </CollectionSummary>
            )}
          </div>
        </Suspense>
      </div>
    </div>
  );
}
