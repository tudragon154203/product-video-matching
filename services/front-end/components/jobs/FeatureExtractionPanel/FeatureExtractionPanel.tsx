'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Sparkles, Layers, Brain, Pointer, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, Video } from 'lucide-react';
import { FeatureStepProgress } from './FeatureStepProgress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MaskGalleryModal } from './MaskGalleryModal';
import type { FeaturesSummaryResponse } from '@/lib/zod/features';

interface FeatureExtractionPanelProps {
  jobId: string;
  summary?: FeaturesSummaryResponse;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  isActive?: boolean; // True when phase is feature_extraction, false when in later phases
}

export function FeatureExtractionPanel({ 
  jobId,
  summary, 
  isLoading = false, 
  isError = false,
  onRetry,
  isActive = true 
}: FeatureExtractionPanelProps) {
  const t = useTranslations('jobFeatureExtraction');

  // State for accordion - must be at top level (hooks rule)
  const [isExpanded, setIsExpanded] = React.useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = sessionStorage.getItem('featureExtractionPanelExpanded');
    return stored !== null ? stored === 'true' : false;
  });

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('featureExtractionPanelExpanded', String(isExpanded));
    }
  }, [isExpanded]);

  const [isMaskModalOpen, setIsMaskModalOpen] = React.useState(false);

  const productSegments = summary?.product_images.segment.done ?? 0;
  const videoSegments = summary?.video_frames.segment.done ?? 0;
  const totalSegments = productSegments + videoSegments;
  const canShowMaskSamples = Boolean(summary && totalSegments > 0);

  const maskButton = canShowMaskSamples ? (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setIsMaskModalOpen(true)}
      className="gap-2"
    >
      <Sparkles className="h-4 w-4 text-amber-500" />
      {t('maskGallery.viewSamples')}
      <span className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
        {t('maskGallery.samplesReady', { count: totalSegments })}
      </span>
    </Button>
  ) : null;

  // If not active (phase has moved past feature_extraction), show collapsible summary
  if (!isActive && summary) {
    const { product_images, video_frames } = summary;

    return (
      <>
      <div className="border rounded-lg overflow-hidden">
        {/* Accordion Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
          aria-expanded={isExpanded}
          aria-controls="feature-extraction-summary-content"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-slate-600" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-600" />
                )}
                <h3 className="font-semibold text-sm">{t('complete.title')}</h3>
              </div>
              
              {/* Show completion badge when collapsed */}
              {!isExpanded && (
                <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Complete
                </Badge>
              )}
            </div>

            {/* Show summary counts when collapsed */}
            {!isExpanded && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Layers className="h-3 w-3" />
                  <span>Images: {product_images.keypoints.done}/{product_images.total}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Video className="h-3 w-3" />
                  <span>Frames: {video_frames.keypoints.done}/{video_frames.total}</span>
                </div>
              </div>
            )}
          </div>
        </button>

        {/* Accordion Content - shows full progress board when expanded */}
        {isExpanded && (
          <div 
            id="feature-extraction-summary-content"
            className="bg-white p-4"
          >
            {/* Render the full progress board */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Product Images Card */}
              <div className="border rounded-lg p-4 space-y-4">
                <div>
                  <h3 className="font-semibold text-lg">{t('productImages.title')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('productImages.total', { count: product_images.total })}
                  </p>
                </div>

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
              </div>

              {/* Video Frames Card */}
              <div className="border rounded-lg p-4 space-y-4">
                <div>
                  <h3 className="font-semibold text-lg">{t('videoFrames.title')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('videoFrames.total', { count: video_frames.total })}
                  </p>
                </div>

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
              </div>
            </div>

            {/* View Samples Button - Centered below panels in expanded view */}
            {maskButton && (
              <div className="flex justify-center mt-6">
                {maskButton}
              </div>
            )}
          </div>
        )}
      </div>
      <MaskGalleryModal
        jobId={jobId}
        open={isMaskModalOpen}
        onOpenChange={setIsMaskModalOpen}
        productSegmentCount={productSegments}
        videoSegmentCount={videoSegments}
        initialType={productSegments > 0 ? 'products' : 'videos'}
      />
      </>
    );
  }

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
    <>
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

      {/* View Samples Button - Centered below panels */}
      {maskButton && (
        <div className="flex justify-center mt-6">
          {maskButton}
        </div>
      )}

      {summary && (
        <MaskGalleryModal
          jobId={jobId}
          open={isMaskModalOpen}
          onOpenChange={setIsMaskModalOpen}
          productSegmentCount={productSegments}
          videoSegmentCount={videoSegments}
          initialType={productSegments > 0 ? 'products' : 'videos'}
        />
      )}
    </>
  );
}
