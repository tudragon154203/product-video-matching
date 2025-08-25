import React from 'react';
import { useTranslations } from 'next-intl';

interface ProductsEmptyProps {}

export function ProductsEmpty({ }: ProductsEmptyProps) {
  const t = useTranslations();
  
  return (
    <div className="text-center py-8">
      <div className="text-muted-foreground">
        {t('products.empty')}
      </div>
    </div>
  );
}