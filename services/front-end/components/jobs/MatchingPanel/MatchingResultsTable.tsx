'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { useJobMatches } from '@/lib/api/hooks';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, CheckCircle, Clock, Image as ImageIcon } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Image from 'next/image';
import { EvidenceDrawer } from './EvidenceDrawer';

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
  const [debouncedMinScore, setDebouncedMinScore] = React.useState(0.8);
  const [selectedMatchId, setSelectedMatchId] = React.useState<string | null>(null);
  const [evidenceOnly, setEvidenceOnly] = React.useState(false);
  const [sortBy, setSortBy] = React.useState<'score' | 'created_at'>('score');
  const [sortOrder, setSortOrder] = React.useState<'asc' | 'desc'>('desc');

  // Debounce min score changes
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedMinScore(minScore);
    }, 300);
    return () => clearTimeout(timer);
  }, [minScore]);

  // Memoize params to prevent unnecessary refetches
  const queryParams = React.useMemo(() => ({
    limit: 100,
    offset: 0,
    min_score: debouncedMinScore,
  }), [debouncedMinScore]);

  const { 
    data: matchesData, 
    isLoading, 
    isError,
    refetch 
  } = useJobMatches(
    jobId,
    queryParams,
    enabled,
    enabled ? 5000 : false // Poll every 5 seconds when enabled
  );

  const matches = matchesData?.items || [];

  // Filter and sort matches
  const filteredMatches = React.useMemo(() => {
    let filtered = evidenceOnly ? matches.filter(m => m.evidence_url) : matches;
    
    // Sort matches
    filtered = [...filtered].sort((a, b) => {
      if (sortBy === 'score') {
        return sortOrder === 'desc' ? b.score - a.score : a.score - b.score;
      } else {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();
        return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
      }
    });
    
    return filtered;
  }, [matches, evidenceOnly, sortBy, sortOrder]);

  // Group matches by product - MUST be before any conditional returns
  const productGroups = React.useMemo(() => {
    const groups = new Map<string, typeof filteredMatches>();
    filteredMatches.forEach((match) => {
      const productKey = match.product_id || 'unknown';
      if (!groups.has(productKey)) {
        groups.set(productKey, []);
      }
      groups.get(productKey)!.push(match);
    });
    return Array.from(groups.entries()).map(([productId, productMatches]) => ({
      productId,
      productTitle: productMatches[0].product_title || 'Product',
      matches: productMatches,
      bestScore: Math.max(...productMatches.map(m => m.score)),
      videoCount: productMatches.length,
    }));
  }, [filteredMatches]);

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

  if (filteredMatches.length === 0) {
    return (
      <div className="border rounded-lg p-8 text-center">
        <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
        <h3 className="font-semibold mb-2">
          {evidenceOnly ? t('empty.noEvidence') : t('empty.title')}
        </h3>
        <p className="text-sm text-muted-foreground">
          {evidenceOnly ? t('empty.evidenceDescription') : t('empty.description')}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h3 className="font-semibold">{t('results.title')}</h3>
        <div className="flex items-center gap-4 flex-wrap">
          {/* Evidence Only Filter */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={evidenceOnly}
              onChange={(e) => setEvidenceOnly(e.target.checked)}
              className="rounded"
            />
            {t('results.evidenceOnly')}
          </label>

          {/* Sort Controls */}
          <div className="flex items-center gap-2 text-sm">
            <label className="text-muted-foreground">{t('results.sortBy')}:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'score' | 'created_at')}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="score">{t('results.score')}</option>
              <option value="created_at">{t('results.createdAt')}</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="px-2 py-1 border rounded hover:bg-slate-50 text-xs"
              title={sortOrder === 'desc' ? t('results.ascending') : t('results.descending')}
            >
              {sortOrder === 'desc' ? '↓' : '↑'}
            </button>
          </div>

          {/* Min Score Slider */}
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
                  className="px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedMatchId(match.match_id)}
                >
                  <div className="flex items-center justify-between gap-4">
                    {/* Evidence Thumbnail */}
                    <div className="flex-shrink-0">
                      {match.evidence_url ? (
                        <div className="relative w-16 h-16 rounded border overflow-hidden bg-slate-100">
                          <Image
                            src={match.evidence_url}
                            alt="Evidence"
                            fill
                            className="object-cover"
                            sizes="64px"
                          />
                        </div>
                      ) : (
                        <div className="w-16 h-16 rounded border bg-slate-100 flex items-center justify-center">
                          <ImageIcon className="h-6 w-6 text-slate-400" />
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {match.video_title || 'Video'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {match.video_platform} • {match.ts ? `${match.ts.toFixed(1)}s` : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(match.created_at).toLocaleString()}
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
                        {match.evidence_url ? (
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

      {matchesData && matchesData.total > filteredMatches.length && (
        <p className="text-sm text-muted-foreground text-center">
          {t('results.showing', { 
            count: filteredMatches.length, 
            total: matchesData.total 
          })}
        </p>
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer
        matchId={selectedMatchId}
        open={!!selectedMatchId}
        onClose={() => setSelectedMatchId(null)}
      />
    </div>
  );
}
