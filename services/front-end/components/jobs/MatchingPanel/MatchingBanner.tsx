'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Zap } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface MatchingBannerProps {
  percent?: number;
  matchesFound?: number;
}

export function MatchingBanner({ 
  percent = 80, 
  matchesFound = 0 
}: MatchingBannerProps) {
  const t = useTranslations('jobMatching');

  return (
    <div 
      className="rounded-lg p-6 bg-gradient-to-r from-purple-50 via-violet-50 to-white border border-purple-200"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <Zap className="h-6 w-6 text-purple-600 mt-1" />
          <div className="space-y-2 flex-1">
            <h2 className="text-lg font-semibold text-purple-900">
              {t('banner.title')}
            </h2>
            <p className="text-sm text-purple-800">
              {t('banner.description')}
            </p>
            {matchesFound > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  {t('banner.matchesFound', { count: matchesFound })}
                </Badge>
              </div>
            )}
          </div>
        </div>
        <Badge className="bg-purple-600 text-white text-sm px-3 py-1">
          {percent}%
        </Badge>
      </div>
    </div>
  );
}
