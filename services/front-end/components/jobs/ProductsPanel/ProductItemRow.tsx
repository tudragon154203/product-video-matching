import React from 'react';
import Link from 'next/link';
import { ProductDetail } from '@/lib/zod/result';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { InlineBadge } from '@/components/jobs/InlineBadge';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { useTranslations } from 'next-intl';

interface ProductItemRowProps {
  product: ProductDetail;
}

export function ProductItemRow({ product }: ProductItemRowProps) {
  const t = useTranslations();
  
  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      <div className="flex-shrink-0">
        <div className="w-16 h-16 bg-muted rounded-md flex items-center justify-center">
          {product.image_url_main ? (
            <img
              src={product.image_url_main}
              alt={product.title}
              className="w-full h-full object-cover rounded-md"
              loading="lazy"
            />
          ) : (
            <div className="text-muted-foreground text-xs">
              No Image
            </div>
          )}
        </div>
      </div>
      
      <div className="flex-1 min-w-0">
        <Link
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium hover:text-primary truncate block"
          title={product.title}
        >
          {product.title}
        </Link>
        
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
        </div>
      </div>
      
      <LinkExternalIcon className="flex-shrink-0 text-muted-foreground" />
    </div>
  );
}