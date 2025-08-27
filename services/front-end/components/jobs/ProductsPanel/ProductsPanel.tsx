'use client';

import React, { useEffect, useCallback } from 'react';
import { usePaginatedListWithPreloading } from '@/lib/hooks/usePaginatedListWithPreloading';
import { productApiService } from '@/lib/api/services/product.api';
import { ProductItem } from '@/lib/zod/product';
import { groupBy } from '@/lib/utils/groupBy';
import { useTranslations } from 'next-intl';

import { PanelHeader } from '@/components/jobs/PanelHeader';
import { PanelSection } from '@/components/jobs/PanelSection';
import { ProductGroup } from './ProductGroup';
import { ProductItemRow } from './ProductItemRow';
import { ProductsPagination } from './ProductsPagination';
import { ProductsSkeleton } from './ProductsSkeleton';
import { ProductsEmpty } from './ProductsEmpty';
import { ProductsError } from './ProductsError';

interface ProductsPanelProps {
  jobId: string;
  isCollecting?: boolean;
}

export function ProductsPanel({ jobId, isCollecting = false }: ProductsPanelProps) {
  const t = useTranslations('jobResults');

  // Fetch function for the hook
  const fetchProductsData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');

    return await productApiService.getJobProducts(jobId, {
      limit,
      offset,
    });
  }, [jobId]);

  const {
    items: products,
    total,
    isLoading,
    isNavigationLoading,
    isPreloading,
    error,
    handlePrev,
    handleNext,
    handleRetry,
    clearCache,
    fetchFunction: fetchProducts,
    loadFromCacheOrFetch,
    pollCurrentPage,
    offset,
    limit
  } = usePaginatedListWithPreloading<ProductItem>(fetchProductsData);



  // Initial load and navigation changes
  useEffect(() => {
    if (!isCollecting) {
      console.log('Data loading effect triggered for offset:', offset);
      loadFromCacheOrFetch();
    }
  }, [offset, loadFromCacheOrFetch, isCollecting]);

  // Auto-refetch when collecting (without showing navigation loading)
  useEffect(() => {
    if (isCollecting) {
      const interval = setInterval(() => pollCurrentPage(), 5000);
      return () => clearInterval(interval);
    }
  }, [isCollecting, pollCurrentPage]);

  // Clear cache when job changes
  useEffect(() => {
    clearCache();
  }, [jobId, clearCache]);

  const groupedProducts = groupBy(products, p => p.src);

  const handleRetryClick = () => {
    handleRetry();
  };

  return (
    <PanelSection data-testid="products-panel">
      <PanelHeader
        title={t('products.panelTitle')}
        count={total}
      />

      {/* Pre-loading indicator */}
      {isPreloading && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 mb-4 text-sm text-blue-800">
          🔄 Pre-loading adjacent pages in background...
        </div>
      )}

      <div className="space-y-4 relative">
        {isNavigationLoading && products.length > 0 && (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg">
            <div className="bg-background border rounded-lg px-4 py-2 shadow-sm flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-muted-foreground">{t('products.loading')}</span>
            </div>
          </div>
        )}
        {isLoading && products.length === 0 ? (
          <ProductsSkeleton count={10} data-testid="products-skeleton" />
        ) : error ? (
          <ProductsError onRetry={handleRetryClick} data-testid="products-error" />
        ) : products.length === 0 ? (
          <ProductsEmpty isCollecting={isCollecting} data-testid="products-empty" />
        ) : (
          Object.entries(groupedProducts).map(([src, items]) => (
            <div key={src}>
              <ProductGroup src={src} count={items.length} />
              <div className="space-y-2">
                {items.map((product) => (
                  <ProductItemRow key={product.product_id} product={product} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {total > 10 && (
        <ProductsPagination
          total={total}
          limit={limit}
          offset={offset}
          onPrev={handlePrev}
          onNext={handleNext}
          isLoading={isNavigationLoading}
          data-testid="products-pagination"
        />
      )}
    </PanelSection>
  );
}