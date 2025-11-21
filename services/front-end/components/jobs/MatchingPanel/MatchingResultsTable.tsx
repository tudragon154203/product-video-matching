'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { useJobMatches } from '@/lib/api/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
  const [minScore, setMinScore] = React.useState(0.5);

  const { 
    data: matchesData, 
    isLoading, 
    isError,
    refetch 
  } = useJobMatches(
    jobId,
    { limit: 25, offset: 0, min_score: minScore },
    enabled
  );

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

  const matches = matchesData?.items || [];

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

      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-600">
                  {t('results.product')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-600">
                  {t('results.video')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-600">
                  {t('results.score')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-600">
                  {t('results.evidence')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {matches.map((match) => (
                <tr key={match.match_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm">
                    {match.product_title || 'Product'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {match.video_title || 'Video'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          {match.score.toFixed(2)}
                        </span>
                      </div>
                      <Progress 
                        value={match.score * 100} 
                        className="h-1 w-20" 
                      />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {match.evidence_path ? (
                      <Badge className="bg-green-100 text-green-800">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        {t('results.ready')}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-amber-600">
                        <Clock className="h-3 w-3 mr-1" />
                        {t('results.pending')}
                      </Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
