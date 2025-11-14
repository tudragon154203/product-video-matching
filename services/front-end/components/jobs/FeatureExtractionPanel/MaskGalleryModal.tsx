'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import { useTranslations } from 'next-intl';
import { X, Image as ImageIcon, Video as VideoIcon, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CommonPagination } from '@/components/CommonPanel/CommonPagination';
import { useProductImageFeatures, useVideoFrameFeatures } from '@/lib/api/hooks';
import { MaskSampleCard } from './MaskSampleCard';
import { cn } from '@/lib/utils';
import type { ProductImageFeatureItem, VideoFrameFeatureItem } from '@/lib/zod/features';

type AssetType = 'products' | 'videos';

interface MaskGalleryModalProps {
  jobId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productSegmentCount?: number;
  videoSegmentCount?: number;
  initialType?: AssetType;
}

const PAGE_SIZE = 12;

const getItemKey = (
  item: ProductImageFeatureItem | VideoFrameFeatureItem
) => {
  return 'img_id' in item ? `img-${item.img_id}` : `frame-${item.frame_id}`;
};

const getDefaultAssetType = (
  initialType?: AssetType,
  productCount?: number,
  videoCount?: number
): AssetType => {
  if (initialType) return initialType;
  if ((productCount ?? 0) > 0) return 'products';
  if ((videoCount ?? 0) > 0) return 'videos';
  return 'products';
};

export function MaskGalleryModal({
  jobId,
  open,
  onOpenChange,
  productSegmentCount,
  videoSegmentCount,
  initialType,
}: MaskGalleryModalProps) {
  const t = useTranslations('jobFeatureExtraction.maskGallery');
  const [isMounted, setIsMounted] = React.useState(false);
  const [productOffset, setProductOffset] = React.useState(0);
  const [frameOffset, setFrameOffset] = React.useState(0);
  const [assetType, setAssetType] = React.useState<AssetType>(() =>
    getDefaultAssetType(initialType, productSegmentCount, videoSegmentCount)
  );
  const [productSeededOffset, setProductSeededOffset] = React.useState(false);
  const [frameSeededOffset, setFrameSeededOffset] = React.useState(false);
  const dialogTitleId = React.useId();
  const dialogDescriptionId = React.useId();
  const closeButtonRef = React.useRef<HTMLButtonElement | null>(null);
  const previousFocusRef = React.useRef<HTMLElement | null>(null);
  const lastOpenRef = React.useRef(false);
  const contentRef = React.useRef<HTMLDivElement | null>(null);
  const scrollContentToTop = React.useCallback(() => {
    const node = contentRef.current;
    if (node) {
      node.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, []);

  React.useEffect(() => setIsMounted(true), []);

  const defaultType = React.useMemo(
    () => getDefaultAssetType(initialType, productSegmentCount, videoSegmentCount),
    [initialType, productSegmentCount, videoSegmentCount]
  );

  React.useEffect(() => {
    if (open && !lastOpenRef.current) {
      previousFocusRef.current = document.activeElement as HTMLElement | null;
      setAssetType(defaultType);
      setProductOffset(0);
      setFrameOffset(0);
      setProductSeededOffset(false);
      setFrameSeededOffset(false);
      document.body.style.setProperty('overflow', 'hidden');
      requestAnimationFrame(() => closeButtonRef.current?.focus());
    } else if (!open && lastOpenRef.current) {
      document.body.style.removeProperty('overflow');
      previousFocusRef.current?.focus();
    }

    lastOpenRef.current = open;

    return () => {
      if (lastOpenRef.current) {
        document.body.style.removeProperty('overflow');
      }
    };
  }, [open, defaultType]);

  const queryEnabled = open && Boolean(jobId);

  const productParams = React.useMemo(
    () => ({
      has: 'segment',
      limit: PAGE_SIZE,
      offset: productOffset,
      sort_by: 'created_at',
      order: 'DESC',
    }),
    [productOffset]
  );

  const frameParams = React.useMemo(
    () => ({
      has: 'segment',
      limit: PAGE_SIZE,
      offset: frameOffset,
      sort_by: 'ts',
      order: 'DESC',
    }),
    [frameOffset]
  );

  const productQuery = useProductImageFeatures(jobId, productParams, queryEnabled);
  const frameQuery = useVideoFrameFeatures(jobId, frameParams, queryEnabled);

  const productItems: ProductImageFeatureItem[] = productQuery.data?.items ?? [];
  const frameItems: VideoFrameFeatureItem[] = frameQuery.data?.items ?? [];
  const productTotal = productQuery.data?.total ?? 0;
  const frameTotal = frameQuery.data?.total ?? 0;

  React.useEffect(() => {
    if (!open || productSeededOffset) return;
    if (!productQuery.data) return;
    const total = productQuery.data.total;
    const maxStart = Math.max(total - PAGE_SIZE, 0);
    if (maxStart <= 0) {
      setProductSeededOffset(true);
      return;
    }
    const randomStart = Math.floor(Math.random() * (maxStart + 1));
    const normalized = Math.floor(randomStart / PAGE_SIZE) * PAGE_SIZE;
    if (normalized !== productOffset) {
      setProductOffset(normalized);
    }
    setProductSeededOffset(true);
  }, [open, productSeededOffset, productQuery.data, productOffset]);

  React.useEffect(() => {
    if (!open || frameSeededOffset) return;
    if (!frameQuery.data) return;
    const total = frameQuery.data.total;
    const maxStart = Math.max(total - PAGE_SIZE, 0);
    if (maxStart <= 0) {
      setFrameSeededOffset(true);
      return;
    }
    const randomStart = Math.floor(Math.random() * (maxStart + 1));
    const normalized = Math.floor(randomStart / PAGE_SIZE) * PAGE_SIZE;
    if (normalized !== frameOffset) {
      setFrameOffset(normalized);
    }
    setFrameSeededOffset(true);
  }, [open, frameSeededOffset, frameQuery.data, frameOffset]);

  const handlePrevProducts = React.useCallback(() => {
    setProductOffset((prev) => Math.max(prev - PAGE_SIZE, 0));
  }, []);

  const handleNextProducts = React.useCallback(() => {
    setProductOffset((prev) => {
      const next = prev + PAGE_SIZE;
      if (next >= productTotal) {
        return prev;
      }
      return next;
    });
  }, [productTotal]);

  const handlePrevFrames = React.useCallback(() => {
    setFrameOffset((prev) => Math.max(prev - PAGE_SIZE, 0));
  }, []);

  const handleNextFrames = React.useCallback(() => {
    setFrameOffset((prev) => {
      const next = prev + PAGE_SIZE;
      if (next >= frameTotal) {
        return prev;
      }
      return next;
    });
  }, [frameTotal]);

  const activeItems =
    assetType === 'products'
      ? productItems
      : frameItems;
  const activeTotal = assetType === 'products' ? productTotal : frameTotal;
  const activeOffset = assetType === 'products' ? productOffset : frameOffset;
  const activeIsLoading =
    assetType === 'products' ? productQuery.isLoading : frameQuery.isLoading;
  const activeIsFetching =
    assetType === 'products' ? productQuery.isFetching : frameQuery.isFetching;
  const activeIsError =
    assetType === 'products' ? productQuery.isError : frameQuery.isError;
  const activeError =
    assetType === 'products'
      ? (productQuery.error as Error | null)
      : (frameQuery.error as Error | null);

  const handlePrevActive =
    assetType === 'products' ? handlePrevProducts : handlePrevFrames;
  const handleNextActive =
    assetType === 'products' ? handleNextProducts : handleNextFrames;

  React.useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onOpenChange(false);
      }
      if (event.key === 'ArrowLeft') {
        handlePrevActive();
      }
      if (event.key === 'ArrowRight') {
        handleNextActive();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange, handlePrevActive, handleNextActive]);

  React.useEffect(() => {
    if (!open) return;
    scrollContentToTop();
  }, [open, assetType, productOffset, frameOffset, scrollContentToTop]);

  if (!isMounted || !open) {
    return null;
  }

  const startItem = activeTotal === 0 ? 0 : activeOffset + 1;
  const endItem =
    activeTotal === 0 ? 0 : Math.min(activeOffset + PAGE_SIZE, activeTotal);

  const countLabel = t('countLabel', {
    start: startItem,
    end: endItem,
    total: activeTotal,
  });

  const showEmptyState =
    !activeIsLoading && !activeIsError && activeItems.length === 0;

  const renderContent = () => {
    if (activeIsError) {
      return (
        <div className="py-16 text-center text-red-600">
          {t('error')}
          {activeError?.message && (
            <p className="mt-2 text-sm text-red-500 break-words">
              {activeError.message}
            </p>
          )}
        </div>
      );
    }

    if (activeIsLoading && activeItems.length === 0) {
      return (
        <div className="py-16 flex flex-col items-center text-muted-foreground gap-3">
          <Loader2 className="h-6 w-6 animate-spin" />
          {t('loading')}
        </div>
      );
    }

    if (showEmptyState) {
      return (
        <div className="py-16 text-center text-muted-foreground">
          {t('empty', { type: t(`assetTabs.${assetType}`) })}
        </div>
      );
    }

    return (
      <div className="grid gap-4 md:grid-cols-2">
        {activeItems.map((item) => (
          <MaskSampleCard key={getItemKey(item)} item={item} />
        ))}
      </div>
    );
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div
        className="absolute inset-0 bg-black/60"
        onClick={() => onOpenChange(false)}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={dialogTitleId}
        aria-describedby={dialogDescriptionId}
        className="relative z-10 w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-2xl bg-white shadow-2xl flex flex-col"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b px-6 py-4">
          <div>
            <h2 id={dialogTitleId} className="text-xl font-semibold">
              {t('title')}
            </h2>
            <p
              id={dialogDescriptionId}
              className="text-sm text-muted-foreground mt-1"
            >
              {t('description')}
            </p>
          </div>

          <Button
            ref={closeButtonRef}
            aria-label={t('close')}
            variant="ghost"
            size="icon"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex gap-2 border-b px-6 py-3 flex-wrap">
          {([
            {
              type: 'products' as AssetType,
              label: t('assetTabs.products'),
              count: productSegmentCount ?? 0,
              icon: <ImageIcon className="h-4 w-4" />,
            },
            {
              type: 'videos' as AssetType,
              label: t('assetTabs.videos'),
              count: videoSegmentCount ?? 0,
              icon: <VideoIcon className="h-4 w-4" />,
            },
          ] as const).map((tab) => (
            <button
              key={tab.type}
              type="button"
              className={cn(
                'flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors',
                assetType === tab.type
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              )}
              onClick={() => setAssetType(tab.type)}
              aria-pressed={assetType === tab.type}
            >
              {tab.icon}
              <span>{tab.label}</span>
              <Badge variant="secondary" className="text-xs">
                {tab.count}
              </Badge>
            </button>
          ))}
        </div>

        <div ref={contentRef} className="flex-1 overflow-auto px-6 py-4">
          {renderContent()}
        </div>

        <div className="border-t px-6 py-4 space-y-2">
          <div className="text-sm text-muted-foreground">{countLabel}</div>
          <CommonPagination
            total={activeTotal}
            limit={PAGE_SIZE}
            offset={activeOffset}
            onPrev={handlePrevActive}
            onNext={handleNextActive}
            isLoading={activeIsFetching}
            testId="mask-gallery-pagination"
          />
          <p className="text-xs text-muted-foreground">
            {t('keyboardHint')}
          </p>
        </div>
      </div>
    </div>,
    document.body
  );
}
