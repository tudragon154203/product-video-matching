import React from 'react';
import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';

interface ProductsErrorProps {
  onRetry: () => void;
  'data-testid'?: string;
}

export function ProductsError({ onRetry, 'data-testid': dataTestId }: ProductsErrorProps) {
  const t = useTranslations();

  return (
    <div className="text-center py-8" data-testid={dataTestId}>
      <div className="text-destructive font-medium mb-2">
        {t('errors.loadFailed')}
      </div>
      <Button onClick={onRetry} variant="outline" size="sm" data-testid="products-retry">
        {t('errors.retry')}
      </Button>
    </div>
  );
}