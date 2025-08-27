import React from 'react';
import { useTranslations } from 'next-intl';

interface ProductsEmptyProps {
  isCollecting?: boolean;
}

export function ProductsEmpty({ isCollecting = false }: ProductsEmptyProps) {
  const t = useTranslations('jobResults');

  return (
    <div className="text-center py-8">
      <div className="text-muted-foreground">
        {isCollecting ? t('products.collecting') : t('products.empty')}
      </div>
    </div>
  );
}