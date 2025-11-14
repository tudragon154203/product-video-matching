'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Sparkles, Layers, Brain, Pointer, AlertCircle, CheckCircle2 } from 'lucide-react';
import { FeatureStepProgress } from './FeatureStepProgress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { FeaturesSummaryResponse } from '@/lib/zod/features';

interface FeatureExtractionPanelProps {
  summary?: FeaturesSummaryResponse;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
}

export function FeatureExtractionPanel({ 
  summary, 
  isLoading = false, 
  isError = false,
  onRetry 
}: FeatureExtractionPanelProps) {
  const t = useTranslations('jobFeatureExtraction');

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="border rounded-lg p-4 space-y-4">
            <div className="h-6 bg-muted rounded animate-pulse w-1/3" />
            <div className="space-y-3">
              {[1, 2, 3].map((j) => (
                <div key={j} className="space-y-2">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                  <div className="h-2 bg-muted rounded animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive" className="border-red-200">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>{t('errors.summaryFailed')}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-sm underline hover:no-underline"
            >
              {t('errors.retry')}
            </button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  if (!summary) {
    return null;
  }

  const { product_images, video_frames } = summary;

  // Check if all steps are complete
  const allComplete = 
    product_images.keypoints.percent >= 100 && 
    video_frames.keypoints.percent >= 100;

  if (allComplete) {
    return (
      <div className="border rounded-lg p-4 bg-emerald-50">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <div>
            <h3 className="font-medium text-emerald-900">{t('complete.title')}</h3>
            <p className="text-sm text-emerald-700">{t('complete.description')}</p>
          </div>
        </div>
      </div>
    );
  }

  // Show alert if no assets
  if (product_images.total === 0 && video_frames.total === 0) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{t('errors.noAssets')}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Product Images Card */}
      <div className="border rounded-lg p-4 space-y-4">
        <div>
          <h3 className="font-semibold text-lg">{t('productImages.title')}</h3>
          <p className="text-sm text-muted-foreground">
            {t('productImages.total', { count: product_images.total })}
          </p>
        </div>

        {product_images.total === 0 ? (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{t('productImages.noAssets')}</AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-4">
            <FeatureStepProgress
              label={t('steps.segment')}
              done={product_images.segment.done}
              total={product_images.total}
              color="sky"
              icon={<Layers className="h-4 w-4" />}
            />
            <FeatureStepProgress
              label={t('steps.embedding')}
              done={product_images.embedding.done}
              total={product_images.total}
              color="indigo"
              icon={<Brain className="h-4 w-4" />}
            />
            <FeatureStepProgress
              label={t('steps.keypoints')}
              done={product_images.keypoints.done}
              total={product_images.total}
              color="pink"
              icon={<Pointer className="h-4 w-4" />}
            />
          </div>
        )}
      </div>

      {/* Video Frames Card */}
      <div className="border rounded-lg p-4 space-y-4">
        <div>
          <h3 className="font-semibold text-lg">{t('videoFrames.title')}</h3>
          <p className="text-sm text-muted-foreground">
            {t('videoFrames.total', { count: video_frames.total })}
          </p>
        </div>

        {video_frames.total === 0 ? (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{t('videoFrames.noAssets')}</AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-4">
            <FeatureStepProgress
              label={t('steps.segment')}
              done={video_frames.segment.done}
              total={video_frames.total}
              color="sky"
              icon={<Layers className="h-4 w-4" />}
            />
            <FeatureStepProgress
              label={t('steps.embedding')}
              done={video_frames.embedding.done}
              total={video_frames.total}
              color="indigo"
              icon={<Brain className="h-4 w-4" />}
            />
            <FeatureStepProgress
              label={t('steps.keypoints')}
              done={video_frames.keypoints.done}
              total={video_frames.total}
              color="pink"
              icon={<Pointer className="h-4 w-4" />}
            />
          </div>
        )}
      </div>
    </div>
  );
}
