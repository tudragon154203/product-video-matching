import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { ProductItem } from '@/lib/zod/product';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { ThumbnailImage } from '@/components/common/ThumbnailImage';
import { imageApiService } from '@/lib/api/services/image.api';

interface ProductItemRowProps {
  product: ProductItem;
  jobId: string;
  isCollecting?: boolean;
}

export function ProductItemRow({ product, jobId, isCollecting = false }: ProductItemRowProps) {
  const t = useTranslations()
  const [thumbnailSrc, setThumbnailSrc] = useState<string | null>(product.primary_image_url ?? null);

  useEffect(() => {
    setThumbnailSrc(product.primary_image_url ?? null);
  }, [product.primary_image_url]);

  useEffect(() => {
    let isCancelled = false;

    if (!jobId || !product.product_id || product.image_count <= 0) {
      return undefined;
    }

    const fetchThumbnail = async () => {
      try {
        const response = await imageApiService.getJobImages(jobId, {
          product_id: product.product_id,
          limit: 1,
          offset: 0,
        });

        if (isCancelled) {
          return;
        }

        const firstImage = response.items[0];

        if (firstImage?.url) {
          setThumbnailSrc(firstImage.url);
        } else if (firstImage?.local_path) {
          setThumbnailSrc(firstImage.local_path);
        } else {
          setThumbnailSrc(product.primary_image_url ?? null);
        }
      } catch (error) {
        if (!isCancelled) {
          setThumbnailSrc(product.primary_image_url ?? null);
        }
      }
    };

    fetchThumbnail();

    return () => {
      isCancelled = true;
    };
  }, [jobId, product.product_id, product.image_count, product.primary_image_url]);

  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      {/* Product Thumbnail */}
      <Link
        href={product.url || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-shrink-0 hover:opacity-80 transition-opacity"
      >
        <ThumbnailImage
          src={thumbnailSrc ?? undefined}
          alt={product.title || t('products.fallbackImage')}
          data-testid="product-thumbnail"
        />
      </Link>

      <div className="flex-1 min-w-0">
        {product.url ? (
          <Link
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-primary hover:text-primary/80 hover:underline truncate block transition-colors"
            title={product.title || t('products.fallbackTitle')}
          >
            {product.title || t('products.fallbackTitle')}
          </Link>
        ) : (
          <div className="text-sm font-medium truncate" title={product.title || t('products.fallbackTitle')}>
            {product.title || t('products.fallbackTitle')}
          </div>
        )}

        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          {product.brand && (
            <span>{product.brand}</span>
          )}
          {product.asin_or_itemid && (
            <span>| {product.asin_or_itemid}</span>
          )}
          {product.created_at && (
            <span>| {formatGMT7(product.created_at)}</span>
          )}
          {product.image_count > 0 && (
            <span>| {product.image_count} {product.image_count === 1 ? t('products.image') : t('products.images')}</span>
          )}
        </div>
      </div>

      {product.url && (
        <Link
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 text-muted-foreground hover:text-primary transition-colors"
        >
          <LinkExternalIcon className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}
