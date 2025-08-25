import React from 'react';
import { useTranslations } from 'next-intl';

interface VideosEmptyProps {}

export function VideosEmpty({ }: VideosEmptyProps) {
  const t = useTranslations();
  
  return (
    <div className="text-center py-8">
      <div className="text-muted-foreground">
        {t('videos.empty')}
      </div>
    </div>
  );
}