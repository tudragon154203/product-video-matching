'use client';

import React, { useCallback } from 'react';
import { productApiService } from '@/lib/api/services/product.api';
import { ProductItem } from '@/lib/zod/product';
import { groupBy } from '@/lib/utils/groupBy';
import { useTranslations } from 'next-intl';
import { queryKeys } from '@/lib/api/hooks';
import { CommonPanelLayout, CommonPagination, usePanelData } from '@/components/CommonPanel';
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList';

import { ProductGroup } from './ProductGroup';
import { ProductItemRow } from './ProductItemRow';
import { ProductsSkeleton } from './ProductsSkeleton';
import { ProductsEmpty } from './ProductsEmpty';
import { ProductsError } from './ProductsError';
import { Badge } from '@/components/ui/badge';

import type { ProductImagesFeatures } from '@/lib/zod/features';
import { Layers, Brain, Pointer } from 'lucide-react';

interface ProductsPanelProps {
  jobId: string;
  isCollecting?: boolean;
  productsDone?: boolean;
  featurePhase?: boolean;
  featureSummary?: ProductImagesFeatures;
}

export function ProductsPanel({ 
  jobId, 
  isCollecting = false, 
  productsDone = false,
  featurePhase = false,
  featureSummary
}: ProductsPanelProps) {
  const t = useTranslations('jobResults');

  // Animation hook for smooth list transitions
  const { parentRef: productsListRef } = useAutoAnimateList<HTMLDivElement>();

  // Fetch function for TanStack Query
  const fetchProductsData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');

    return await productApiService.getJobProducts(jobId, {
      limit,
      offset,
    });
  }, [jobId]);

  const {
    items: products = [],
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
  } = usePanelData<ProductItem>({
    jobId,
    isCollecting,
    limit: 10,
    fetchFunction: fetchProductsData,
    queryKey: (offset, limit) => [...queryKeys.products.byJob(jobId, { offset, limit })],
    enabled: !!jobId,
  });

  const groupedProducts = groupBy(products, p => p.src);

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
      title={t('products.panelTitle')}
      count={total}
      headerChildren={
        productsDone ? (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs text-green-600">✔ Products done</Badge>
          </div>
        ) : null
      }
      footerChildren={renderFeatureToolbar()}
      isPlaceholderData={isPlaceholderData}
      isNavigationLoading={isNavigationLoading}
      isLoading={isLoading}
      isError={isError}
      isEmpty={products.length === 0}
      error={error}
      onRetry={handleRetryClick}
      testId="products-panel"
      skeletonComponent={<ProductsSkeleton count={10} data-testid="products-skeleton" />}
      emptyComponent={<ProductsEmpty isCollecting={isCollecting} data-testid="products-empty" />}
      errorComponent={<ProductsError onRetry={handleRetryClick} data-testid="products-error" />}
    >
      <div ref={productsListRef}>
        {Object.entries(groupedProducts).map(([src, items]) => (
          <div key={src}>
            <ProductGroup src={src} count={items.length} />
            <div className="space-y-2">
              {items.map((product) => (
                <ProductItemRow key={product.product_id} product={product} jobId={jobId} isCollecting={isCollecting} />
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
          testId="products-pagination"
        />
      )}
    </CommonPanelLayout>
  );
}
