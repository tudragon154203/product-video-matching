import React from 'react';
import Link from 'next/link';
import { ProductItem } from '@/lib/zod/product';
import { formatGMT7 } from '@/lib/utils/formatGMT7';
import { InlineBadge } from '@/components/jobs/InlineBadge';
import { LinkExternalIcon } from '@/components/jobs/LinkExternalIcon';
import { useTranslations } from 'next-intl';

interface ProductItemRowProps {
  product: ProductItem;
}

export function ProductItemRow({ product }: ProductItemRowProps) {
  const t = useTranslations();
  
  return (
    <div className="flex items-center gap-3 p-2 hover:bg-muted rounded-md transition-colors">
      <div className="flex-shrink-0">
        <Link
          href={product.url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-16 h-16 bg-muted rounded-md flex items-center justify-center hover:bg-muted/80 transition-colors"
        >
          <div className="text-muted-foreground text-xs text-center">
            {product.image_count} {product.image_count === 1 ? 'image' : 'images'}
          </div>
        </Link>
      </div>
      
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