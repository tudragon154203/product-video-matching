import React from 'react';
import Link from 'next/link';
import { ProductItem } from '@/lib/zod/product';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { InlineBadge } from '@/components/jobs/InlineBadge';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { ThumbnailImage } from '@/components/common/ThumbnailImage';
import { useJobImages } from '@/lib/api/hooks';
import { useTranslations } from 'next-intl';

interface ProductItemRowProps {
  product: ProductItem;
  jobId: string;
  isCollecting?: boolean;
}

export function ProductItemRow({ product, jobId, isCollecting = false }: ProductItemRowProps) {
  const t = useTranslations();

  // Fetch first image for this product
  // Reduce API load: skip nested image fetches while collecting
  const { data: imagesResponse } = useJobImages(
    jobId,
    {
      product_id: product.product_id,
      limit: 1, // Only fetch the first image
      offset: 0
    },
    !!jobId && !!product.product_id && !isCollecting
  );

  const firstImage = isCollecting ? undefined : imagesResponse?.items?.[0];

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
          src={firstImage?.url}
          alt={product.title || 'Product image'}
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
            title={product.title || 'Untitled Product'}
          >
            {product.title || 'Untitled Product'}
          </Link>
        ) : (
          <div className="text-sm font-medium truncate" title={product.title || 'Untitled Product'}>
            {product.title || 'Untitled Product'}
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
            <span>| {product.image_count} {product.image_count === 1 ? 'image' : 'images'}</span>
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
