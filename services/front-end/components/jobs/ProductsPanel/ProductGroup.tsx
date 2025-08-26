import React from 'react';
import { InlineBadge } from '@/components/jobs/InlineBadge';
import { useTranslations } from 'next-intl';

interface ProductGroupProps {
  src: string;
  count: number;
}

export function ProductGroup({ src, count }: ProductGroupProps) {
  const t = useTranslations('jobResults.meta');
  const labelMap: Record<string, string> = {
    'amazon': 'Amazon',
    'ebay': 'eBay',
  };

  const label = labelMap[src.toLowerCase()] || src;

  return (
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-2">
        <InlineBadge text={label} />
        <span className="text-sm text-muted-foreground">
          {count} {t('product')}
        </span>
      </div>
    </div>
  );
}