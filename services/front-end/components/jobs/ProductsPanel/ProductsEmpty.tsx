import React from 'react';
import { useTranslations } from 'next-intl';

interface ProductsEmptyProps {
 isCollecting?: boolean;
  'data-testid'?: string;
}

export function ProductsEmpty({ isCollecting = false, 'data-testid': dataTestId }: ProductsEmptyProps) {
  const t = useTranslations('jobResults');

  return (
    <div className="text-center py-8" data-testid={dataTestId}>
      <div className="text-muted-foreground">
        {isCollecting ? t('products.collecting') : t('products.empty')}
      </div>
    </div>
  );
}