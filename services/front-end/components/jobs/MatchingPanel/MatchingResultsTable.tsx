'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { useJobMatches } from '@/lib/api/hooks';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface MatchingResultsTableProps {
  jobId: string;
  enabled?: boolean;
}

export function MatchingResultsTable({ 
  jobId, 
  enabled = true 
}: MatchingResultsTableProps) {
  const t = useTranslations('jobMatching');
  const [minScore, setMinScore] = React.useState(0.8);

  const { 
    data: matchesData, 
    isLoading, 
    isError,
    refetch 
  } = useJobMatches(
    jobId,
    { limit: 25, offset: 0, min_score: minScore },
    enabled,
    enabled ? 5000 : false // Poll every 5 seconds when enabled
  );

  const matches = matchesData?.items || [];

  // Group matches by product - MUST be before any conditional returns
  const productGroups = React.useMemo(() => {
    const groups = new Map<string, typeof matches>();
    matches.forEach((match) => {
      const productKey = match.product_id || 'unknown';
      if (!groups.has(productKey)) {
        groups.set(productKey, []);
      }
      groups.get(productKey)!.push(match);
    });
    return Array.from(groups.entries()).map(([productId, productMatches]) => ({
      productId,
      productTitle: productMatches[0].product_title || 'Product',
      matches: productMatches.sort((a, b) => b.score - a.score),
      bestScore: Math.max(...productMatches.map(m => m.score)),
      videoCount: productMatches.length,
    }));
  }, [matches]);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-muted rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>{t('errors.matchesFailed')}</span>
          <button
            onClick={() => refetch()}
            className="text-sm underline hover:no-underline"
          >
            {t('errors.retry')}
          </button>
        </AlertDescription>
      </Alert>
    );
  }

  if (matches.length === 0) {
    return (
      <div className="border rounded-lg p-8 text-center">
        <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
        <h3 className="font-semibold mb-2">{t('empty.title')}</h3>
        <p className="text-sm text-muted-foreground">
          {t('empty.description')}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t('results.title')}</h3>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">
            {t('results.minScore')}:
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-32"
          />
          <span className="text-sm font-medium w-12">{minScore.toFixed(2)}</span>
        </div>
      </div>

      <div className="space-y-3">
        {productGroups.map((group) => (
          <div key={group.productId} className="border rounded-lg overflow-hidden">
            {/* Product Header */}
            <div className="bg-slate-50 px-4 py-3 border-b">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-base">{group.productTitle}</h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    {group.videoCount} {group.videoCount === 1 ? 'video' : 'videos'} • 
                    Best score: {group.bestScore.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>

            {/* Video Matches */}
            <div className="divide-y">
              {group.matches.map((match) => (
                <div 
                  key={match.match_id} 
                  className="px-4 py-3 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {match.video_title || 'Video'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Match ID: {match.match_id.substring(0, 8)}...
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {/* Score */}
                      <div className="flex items-center gap-2">
                        <div className="text-right">
                          <div className="text-sm font-medium">
                            {match.score.toFixed(2)}
                          </div>
                          <Progress 
                            value={match.score * 100} 
                            className="h-1 w-16" 
                          />
                        </div>
                      </div>

                      {/* Evidence Badge */}
                      <div className="w-24">
                        {match.evidence_path ? (
                          <Badge className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {t('results.ready')}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-amber-600 text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            {t('results.pending')}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {matchesData && matchesData.total > matches.length && (
        <p className="text-sm text-muted-foreground text-center">
          {t('results.showing', { 
            count: matches.length, 
            total: matchesData.total 
          })}
        </p>
      )}
    </div>
  );
}
