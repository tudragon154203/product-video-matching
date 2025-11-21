'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { TrendingUp, CheckCircle, Image } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import type { MatchingSummaryResponse } from '@/lib/zod/matching';

interface MatchingSummaryCardsProps {
  summary: MatchingSummaryResponse;
}

export function MatchingSummaryCards({ summary }: MatchingSummaryCardsProps) {
  const t = useTranslations('jobMatching');

  const progressPercent = summary.candidates_total > 0
    ? Math.round((summary.candidates_processed / summary.candidates_total) * 100)
    : 0;

  const evidencePercent = summary.matches_found > 0
    ? Math.round((summary.matches_with_evidence / summary.matches_found) * 100)
    : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Pairs Processed Card */}
      <div className="border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-sm">{t('cards.pairsProcessed')}</h4>
          <TrendingUp className="h-4 w-4 text-purple-600" />
        </div>
        <div className="space-y-2">
          <Progress value={progressPercent} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{summary.candidates_processed.toLocaleString()}</span>
            <span>{summary.candidates_total.toLocaleString()}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {progressPercent}% {t('cards.complete')}
          </p>
        </div>
      </div>

      {/* Matches Found Card */}
      <div className="border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-sm">{t('cards.matchesFound')}</h4>
          <CheckCircle className="h-4 w-4 text-green-600" />
        </div>
        <div className="space-y-2">
          <div className="text-3xl font-bold text-green-600">
            {summary.matches_found}
          </div>
          {summary.avg_score && (
            <p className="text-xs text-muted-foreground">
              {t('cards.avgScore')}: {summary.avg_score.toFixed(2)}
            </p>
          )}
          {summary.p90_score && (
            <p className="text-xs text-muted-foreground">
              {t('cards.p90Score')}: {summary.p90_score.toFixed(2)}
            </p>
          )}
        </div>
      </div>

      {/* Evidence Ready Card */}
      <div className="border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-sm">{t('cards.evidenceReady')}</h4>
          <Image className="h-4 w-4 text-blue-600" />
        </div>
        <div className="space-y-2">
          <Progress value={evidencePercent} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{summary.matches_with_evidence}</span>
            <span>{summary.matches_found}</span>
          </div>
          {summary.matches_found > 0 && summary.matches_with_evidence < summary.matches_found && (
            <p className="text-xs text-amber-600">
              {t('cards.evidencePending')}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
