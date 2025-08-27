import React from 'react';
import { useTranslations } from 'next-intl';

interface VideosEmptyProps {
 isCollecting?: boolean;
  'data-testid'?: string;
}

export function VideosEmpty({ isCollecting = false, 'data-testid': dataTestId }: VideosEmptyProps) {
  const t = useTranslations('jobResults');

  return (
    <div className="text-center py-8" data-testid={dataTestId}>
      <div className="text-muted-foreground">
        {isCollecting ? t('videos.collecting') : t('videos.empty')}
      </div>
    </div>
  );
}