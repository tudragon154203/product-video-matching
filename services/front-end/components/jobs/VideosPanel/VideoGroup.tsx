import React from 'react';
import { InlineBadge } from '@/components/jobs/InlineBadge';
import { useTranslations } from 'next-intl';

interface VideoGroupProps {
  platform: string;
  count: number;
}

export function VideoGroup({ platform, count }: VideoGroupProps) {
  const t = useTranslations();
  
  const labelMap: Record<string, string> = {
    'youtube': 'YouTube',
    'tiktok': 'TikTok',
  };

  const label = labelMap[platform.toLowerCase()] || platform;

  return (
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-2">
        <InlineBadge text={label} />
        <span className="text-sm text-muted-foreground">
          {count} {count === 1 ? t('meta.video') : t('meta.videos')}
        </span>
      </div>
    </div>
  );
}