'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { usePaginatedList } from '@/lib/hooks/usePaginatedList';
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
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isNavigationLoading, setIsNavigationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pagination = usePaginatedList(0, 10);

  const fetchProducts = useCallback(async (showNavigationLoading = false, isAlreadyLoading = false) => {
    if (!jobId) return;

    try {
      setIsLoading(true);
      if (showNavigationLoading && !isAlreadyLoading) {
        setIsNavigationLoading(true);
      }
      setError(null);

      const response = await productApiService.getJobProducts(jobId, {
        limit: pagination.limit,
        offset: pagination.offset,
      });

      setProducts(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.loadFailed'));
      setProducts([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
      setIsNavigationLoading(false);
    }
  }, [jobId, pagination.limit, pagination.offset, t]);

  useEffect(() => {
    if (!isCollecting) {
      fetchProducts(true); // Show loading for initial load
    }
  }, [fetchProducts, isCollecting]);

  // Auto-refetch when collecting (without showing navigation loading)
  useEffect(() => {
    if (isCollecting) {
      const interval = setInterval(() => fetchProducts(false), 5000);
      return () => clearInterval(interval);
    }
  }, [isCollecting, fetchProducts]);

  // Handle navigation changes with loading indicators
  useEffect(() => {
    if (!isCollecting && isNavigationLoading) {
      fetchProducts(true, true); // Show loading for pagination navigation, already loading
    }
  }, [pagination.offset, fetchProducts, isCollecting, isNavigationLoading]);

  const groupedProducts = groupBy(products, p => p.src);

  const handleRetry = () => {
    fetchProducts(true);
  };

  const handlePrev = () => {
    setIsNavigationLoading(true); // Set loading immediately
    pagination.prev();
  };

  const handleNext = () => {
    setIsNavigationLoading(true); // Set loading immediately
    pagination.next(total);
  };

  return (
    <PanelSection>
      <PanelHeader
        title={t('products.panelTitle')}
        count={total}
      />

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
          <ProductsSkeleton count={10} />
        ) : error ? (
          <ProductsError onRetry={handleRetry} />
        ) : products.length === 0 ? (
          <ProductsEmpty isCollecting={isCollecting} />
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
          limit={pagination.limit}
          offset={pagination.offset}
          onPrev={handlePrev}
          onNext={handleNext}
          isLoading={isNavigationLoading}
        />
      )}
    </PanelSection>
  );
}