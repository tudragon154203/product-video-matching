'use client';

import React, { useCallback } from 'react';
import { productApiService } from '@/lib/api/services/product.api';
import { ProductItem } from '@/lib/zod/product';
import { groupBy } from '@/lib/utils/groupBy';
import { useTranslations } from 'next-intl';
import { queryKeys } from '@/lib/api/hooks';
import { CommonPanelLayout, CommonPagination, usePanelData } from '@/components/CommonPanel';

import { ProductGroup } from './ProductGroup';
import { ProductItemRow } from './ProductItemRow';
import { ProductsSkeleton } from './ProductsSkeleton';
import { ProductsEmpty } from './ProductsEmpty';
import { ProductsError } from './ProductsError';

interface ProductsPanelProps {
  jobId: string;
  isCollecting?: boolean;
}

export function ProductsPanel({ jobId, isCollecting = false }: ProductsPanelProps) {
  const t = useTranslations('jobResults');

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

  return (
    <CommonPanelLayout
      title={t('products.panelTitle')}
      count={total}
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
