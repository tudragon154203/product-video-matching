'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface FeatureExtractionBannerProps {
  percent?: number;
  counts: {
    products: number;
    videos: number;
    images: number;
    frames: number;
  };
}

export function FeatureExtractionBanner({ percent = 50, counts }: FeatureExtractionBannerProps) {
  const t = useTranslations('jobFeatureExtraction');

  return (
    <div 
      className="rounded-lg p-6 bg-gradient-to-r from-yellow-50 via-amber-50 to-white border border-yellow-200"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <Sparkles className="h-6 w-6 text-yellow-600 mt-1" />
          <div className="space-y-2 flex-1">
            <h2 className="text-lg font-semibold text-yellow-900">
              {t('banner.title')}
            </h2>
            <p className="text-sm text-yellow-800">
              {t('banner.description')}
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              <Badge variant="outline" className="text-xs">
                {t('banner.products', { count: counts.products })}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {t('banner.videos', { count: counts.videos })}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {t('banner.images', { count: counts.images })}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {t('banner.frames', { count: counts.frames })}
              </Badge>
            </div>
          </div>
        </div>
        <Badge className="bg-yellow-600 text-white text-sm px-3 py-1">
          {percent}%
        </Badge>
      </div>
    </div>
  );
}
