'use client';

import React, { useState, useEffect } from 'react';
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
  const t = useTranslations();
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const pagination = usePaginatedList(0, 10);

  const fetchProducts = async () => {
    if (!jobId) return;
    
    try {
      setIsLoading(true);
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
    }
  };

  useEffect(() => {
    if (!isCollecting) {
      fetchProducts();
    }
  }, [jobId, pagination.offset, isCollecting]);

  // Auto-refetch when collecting
  useEffect(() => {
    if (isCollecting) {
      const interval = setInterval(fetchProducts, 5000);
      return () => clearInterval(interval);
    }
  }, [isCollecting, jobId]);

  const groupedProducts = groupBy(products, p => p.src);
  
  const handleRetry = () => {
    fetchProducts();
  };

  const handlePrev = () => {
    pagination.prev();
  };

  const handleNext = () => {
    pagination.next(total);
  };

  return (
    <PanelSection>
      <PanelHeader
        title={t('products.panelTitle')}
        count={total}
      />
      
      <div className="space-y-4">
        {isLoading && products.length === 0 ? (
          <ProductsSkeleton count={10} />
        ) : error ? (
          <ProductsError onRetry={handleRetry} />
        ) : products.length === 0 ? (
          <ProductsEmpty />
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
          isLoading={isLoading}
        />
      )}
    </PanelSection>
  );
}