'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { resultsApiService } from '@/lib/api/services/result.api';
import { X, Download, ExternalLink, Loader2, AlertCircle } from 'lucide-react';
import Image from 'next/image';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface EvidenceDrawerProps {
  matchId: string | null;
  open: boolean;
  onClose: () => void;
}

export function EvidenceDrawer({ matchId, open, onClose }: EvidenceDrawerProps) {
  const t = useTranslations('jobMatching');
  const [matchData, setMatchData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!matchId || !open) {
      setMatchData(null);
      setError(null);
      return;
    }

    const fetchMatchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await resultsApiService.getMatch(matchId);
        setMatchData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load match details');
      } finally {
        setLoading(false);
      }
    };

    fetchMatchData();

    // Poll for evidence if it's not ready yet
    let pollInterval: NodeJS.Timeout | null = null;
    if (matchData && !matchData.evidence_url) {
      pollInterval = setInterval(async () => {
        try {
          const data = await resultsApiService.getMatch(matchId);
          setMatchData(data);
          // Stop polling once evidence is ready
          if (data.evidence_url && pollInterval) {
            clearInterval(pollInterval);
          }
        } catch (err) {
          // Silently fail polling attempts
        }
      }, 3000); // Poll every 3 seconds
    }

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [matchId, open, matchData?.evidence_url]);

  if (!open) return null;

  const buildVideoUrl = (videoUrl: string | null, timestamp: number | null) => {
    if (!videoUrl) return null;
    if (!timestamp) return videoUrl;
    
    // YouTube timestamp
    if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {
      const url = new URL(videoUrl);
      url.searchParams.set('t', Math.floor(timestamp).toString());
      return url.toString();
    }
    
    return videoUrl;
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl z-50 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t('evidence.title')}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {matchData && (
            <>
              {/* Evidence Image */}
              {matchData.evidence_url ? (
                <div className="space-y-3">
                  <div className="relative w-full aspect-video rounded-lg border overflow-hidden bg-slate-100">
                    <Image
                      src={matchData.evidence_url}
                      alt="Evidence"
                      fill
                      className="object-contain"
                      sizes="(max-width: 768px) 100vw, 50vw"
                      priority
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(matchData.evidence_url, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      {t('evidence.openFull')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = matchData.evidence_url;
                        link.download = `evidence_${matchData.match_id}.jpg`;
                        link.click();
                      }}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      {t('evidence.download')}
                    </Button>
                  </div>
                </div>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {t('evidence.pending')}
                  </AlertDescription>
                </Alert>
              )}

              {/* Match Details */}
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold mb-2">{t('evidence.matchDetails')}</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">{t('evidence.score')}:</span>
                      <span className="ml-2 font-medium">{matchData.score.toFixed(3)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('evidence.timestamp')}:</span>
                      <span className="ml-2 font-medium">
                        {matchData.ts ? `${matchData.ts.toFixed(1)}s` : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Product Info */}
                <div>
                  <h3 className="font-semibold mb-2">{t('evidence.product')}</h3>
                  <div className="border rounded-lg p-3 space-y-2">
                    <p className="font-medium">{matchData.product.title || 'Untitled Product'}</p>
                    {matchData.product.brand && (
                      <p className="text-sm text-muted-foreground">
                        {t('evidence.brand')}: {matchData.product.brand}
                      </p>
                    )}
                    {matchData.product.url && (
                      <Button
                        variant="link"
                        size="sm"
                        className="p-0 h-auto"
                        onClick={() => window.open(matchData.product.url, '_blank')}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        {t('evidence.viewProduct')}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Video Info */}
                <div>
                  <h3 className="font-semibold mb-2">{t('evidence.video')}</h3>
                  <div className="border rounded-lg p-3 space-y-2">
                    <p className="font-medium">{matchData.video.title || 'Untitled Video'}</p>
                    <div className="flex items-center gap-2">
                      {matchData.video.platform && (
                        <Badge variant="outline" className="text-xs">
                          {matchData.video.platform}
                        </Badge>
                      )}
                      {matchData.video.duration_s && (
                        <span className="text-sm text-muted-foreground">
                          {Math.floor(matchData.video.duration_s / 60)}:
                          {(matchData.video.duration_s % 60).toString().padStart(2, '0')}
                        </span>
                      )}
                    </div>
                    {matchData.video.url && (
                      <div className="flex gap-2">
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 h-auto"
                          onClick={() => {
                            const url = buildVideoUrl(matchData.video.url, matchData.ts);
                            window.open(url || matchData.video.url, '_blank');
                          }}
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          {matchData.ts 
                            ? t('evidence.openVideoAt', { time: matchData.ts.toFixed(1) })
                            : t('evidence.openVideo')
                          }
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Metadata */}
                <div className="text-xs text-muted-foreground space-y-1 pt-4 border-t">
                  <p>Match ID: {matchData.match_id}</p>
                  <p>Job ID: {matchData.job_id}</p>
                  {matchData.best_img_id && <p>Image ID: {matchData.best_img_id}</p>}
                  {matchData.best_frame_id && <p>Frame ID: {matchData.best_frame_id}</p>}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
