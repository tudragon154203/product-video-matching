import React from 'react';
import { useTranslations } from 'next-intl';

interface VideosEmptyProps {
  isCollecting?: boolean;
}

export function VideosEmpty({ isCollecting = false }: VideosEmptyProps) {
  const t = useTranslations('jobResults');

  return (
    <div className="text-center py-8">
      <div className="text-muted-foreground">
        {isCollecting ? t('videos.collecting') : t('videos.empty')}
      </div>
    </div>
  );
}