'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { 
  Zap, 
  AlertCircle, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp,
  Clock,
  TrendingUp
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MatchingSummaryCards } from './MatchingSummaryCards';
import { MatchingHealthRow } from './MatchingHealthRow';
import { MatchingResultsTable } from './MatchingResultsTable';
import type { MatchingSummaryResponse } from '@/lib/zod/matching';

interface MatchingPanelProps {
  jobId: string;
  summary?: MatchingSummaryResponse;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  isActive?: boolean;
}

export function MatchingPanel({
  jobId,
  summary,
  isLoading = false,
  isError = false,
  onRetry,
  isActive = true
}: MatchingPanelProps) {
  const t = useTranslations('jobMatching');

  const [isExpanded, setIsExpanded] = React.useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = sessionStorage.getItem('matchingPanelExpanded');
    if (stored !== null) {
      return stored === 'true';
    }
    return isActive;
  });

  const prevIsActiveRef = React.useRef(isActive);
  React.useEffect(() => {
    if (prevIsActiveRef.current && !isActive && isExpanded) {
      setIsExpanded(false);
    }
    prevIsActiveRef.current = isActive;
  }, [isActive, isExpanded]);

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('matchingPanelExpanded', String(isExpanded));
    }
  }, [isExpanded]);

  // Collapsed summary view for completed phase
  if (!isActive && summary) {
    const duration = summary.started_at && summary.completed_at
      ? Math.round(
          (new Date(summary.completed_at).getTime() - 
           new Date(summary.started_at).getTime()) / 1000
        )
      : null;

    return (
      <div className="border rounded-lg overflow-hidden">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
          aria-expanded={isExpanded}
          aria-controls="matching-summary-content"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-slate-600" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-600" />
                )}
                <h3 className="font-semibold text-sm">{t('complete.title')}</h3>
              </div>

              {!isExpanded && (
                <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Complete
                </Badge>
              )}
            </div>

            {!isExpanded && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  <span>Matches: {summary.matches_found}</span>
                </div>
                {summary.avg_score && (
                  <div className="flex items-center gap-1">
                    <span>Avg: {summary.avg_score.toFixed(2)}</span>
                  </div>
                )}
                {duration && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{Math.floor(duration / 60)}m {duration % 60}s</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </button>

        {isExpanded && (
          <div id="matching-summary-content" className="bg-white p-4 space-y-4">
            <MatchingSummaryCards summary={summary} />
            <MatchingHealthRow summary={summary} />
            <MatchingResultsTable jobId={jobId} enabled={isExpanded} />
          </div>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-24 bg-muted rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive" className="border-red-200">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>{t('errors.summaryFailed')}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-sm underline hover:no-underline"
            >
              {t('errors.retry')}
            </button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="space-y-4">
      <MatchingSummaryCards summary={summary} />
      <MatchingHealthRow summary={summary} />
      <MatchingResultsTable jobId={jobId} enabled={isActive} />
    </div>
  );
}
