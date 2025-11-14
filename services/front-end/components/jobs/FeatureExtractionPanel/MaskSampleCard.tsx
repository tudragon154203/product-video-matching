'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { AlertCircle } from 'lucide-react';
import type { ProductImageFeatureItem, VideoFrameFeatureItem } from '@/lib/zod/features';
import { cn } from '@/lib/utils';

interface MaskSampleCardProps {
  item: ProductImageFeatureItem | VideoFrameFeatureItem;
}

const isProductItem = (
  item: ProductImageFeatureItem | VideoFrameFeatureItem
): item is ProductImageFeatureItem => {
  return (item as ProductImageFeatureItem).product_id !== undefined;
};

const formatTimestamp = (seconds: number): string => {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0:00';
  }
  const totalSeconds = Math.floor(seconds);
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export function MaskSampleCard({ item }: MaskSampleCardProps) {
  const t = useTranslations('jobFeatureExtraction.maskGallery');
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = React.useState(false);
  const [originalLoaded, setOriginalLoaded] = React.useState(false);
  const [maskLoaded, setMaskLoaded] = React.useState(false);
  const [originalError, setOriginalError] = React.useState(false);
  const [maskError, setMaskError] = React.useState(false);

  React.useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.2 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const originalLabel = t('originalLabel');
  const maskLabel = t('maskLabel');

  const metadata = isProductItem(item)
    ? [
        { label: t('metadata.imageId'), value: item.img_id },
        { label: t('metadata.productId'), value: item.product_id },
      ]
    : [
        { label: t('metadata.frameId'), value: item.frame_id },
        { label: t('metadata.videoId'), value: item.video_id },
        { label: t('metadata.timestamp'), value: formatTimestamp(item.ts) },
      ];

  const originalAlt = isProductItem(item)
    ? t('originalAlt.product', { id: item.img_id })
    : t('originalAlt.video', { id: item.frame_id });

  const maskAlt = isProductItem(item)
    ? t('maskAlt.product', { id: item.img_id })
    : t('maskAlt.video', { id: item.frame_id });

  const shouldLoadOriginal = Boolean(isVisible && item.original_url && !originalError);
  const shouldLoadMask = Boolean(isVisible && item.paths.segment && !maskError);

  return (
    <div
      ref={containerRef}
      className="border rounded-lg bg-white shadow-sm overflow-hidden"
    >
      <div className="grid gap-4 p-4 md:grid-cols-2">
        <figure>
          <figcaption className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
            {originalLabel}
          </figcaption>
          <div className="relative aspect-video rounded-md border bg-slate-50 overflow-hidden flex items-center justify-center">
            {shouldLoadOriginal ? (
              <>
                {!originalLoaded && (
                  <div className="absolute inset-0 bg-slate-200 animate-pulse" />
                )}
                <img
                  src={item.original_url ?? undefined}
                  alt={originalAlt}
                  className={cn(
                    'h-full w-full object-contain transition-opacity duration-200',
                    originalLoaded ? 'opacity-100' : 'opacity-0'
                  )}
                  onLoad={() => setOriginalLoaded(true)}
                  onError={() => setOriginalError(true)}
                />
              </>
            ) : (
              <div className="text-sm text-muted-foreground text-center px-4">
                {originalError ? (
                  <span className="flex items-center justify-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    {t('missingOriginal')}
                  </span>
                ) : (
                  t('missingOriginal')
                )}
              </div>
            )}
          </div>
        </figure>

        <figure>
          <figcaption className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
            {maskLabel}
          </figcaption>
          <div className="relative aspect-video rounded-md border bg-slate-50 overflow-hidden flex items-center justify-center">
            {shouldLoadMask ? (
              <>
                {!maskLoaded && (
                  <div className="absolute inset-0 bg-slate-200 animate-pulse" />
                )}
                <img
                  src={item.paths.segment ?? undefined}
                  alt={maskAlt}
                  className={cn(
                    'h-full w-full object-contain transition-opacity duration-200',
                    maskLoaded ? 'opacity-100' : 'opacity-0'
                  )}
                  onLoad={() => setMaskLoaded(true)}
                  onError={() => setMaskError(true)}
                />
              </>
            ) : (
              <div className="text-sm text-muted-foreground text-center px-4">
                {maskError ? (
                  <span className="flex items-center justify-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    {t('missingMask')}
                  </span>
                ) : (
                  t('missingMask')
                )}
              </div>
            )}
          </div>
        </figure>
      </div>

      <div className="px-4 pb-4 text-xs text-muted-foreground space-y-1">
        {metadata.map(({ label, value }) => (
          <div key={`${label}-${value}`} className="flex justify-between">
            <span className="font-medium">{label}</span>
            <span className="text-slate-900">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
