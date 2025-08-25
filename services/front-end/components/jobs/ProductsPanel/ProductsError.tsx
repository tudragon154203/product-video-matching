import React from 'react';
import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';

interface ProductsErrorProps {
  onRetry: () => void;
}

export function ProductsError({ onRetry }: ProductsErrorProps) {
  const t = useTranslations();
  
  return (
    <div className="text-center py-8">
      <div className="text-destructive font-medium mb-2">
        {t('errors.loadFailed')}
      </div>
      <Button onClick={onRetry} variant="outline" size="sm">
        {t('errors.retry')}
      </Button>
    </div>
  );
}