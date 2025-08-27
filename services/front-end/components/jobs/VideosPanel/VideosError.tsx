import React from 'react';
import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';

interface VideosErrorProps {
  onRetry: () => void;
}

export function VideosError({ onRetry }: VideosErrorProps) {
  const t = useTranslations();

  return (
    <div className="text-center py-8">
      <div className="text-destructive font-medium mb-2">
        {t('errors.loadFailed')}
      </div>
      <Button onClick={onRetry} variant="outline" size="sm" data-testid="videos-retry">
        {t('errors.retry')}
      </Button>
    </div>
  );
}