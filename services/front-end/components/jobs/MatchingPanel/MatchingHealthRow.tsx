'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Activity, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { MatchingSummaryResponse } from '@/lib/zod/matching';

interface MatchingHealthRowProps {
  summary: MatchingSummaryResponse;
}

export function MatchingHealthRow({ summary }: MatchingHealthRowProps) {
  const t = useTranslations('jobMatching');

  const statusColor = {
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    pending: 'bg-gray-100 text-gray-800',
  }[summary.status] || 'bg-gray-100 text-gray-800';

  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-lg">
      {/* Status */}
      <Badge className={statusColor}>
        <Activity className="h-3 w-3 mr-1" />
        {t(`status.${summary.status}`)}
      </Badge>

      {/* Queue Depth */}
      {summary.queue_depth > 0 && (
        <Badge 
          variant="outline" 
          className={summary.queue_depth > 50 ? 'border-amber-500 text-amber-700' : ''}
        >
          {t('health.queueDepth')}: {summary.queue_depth}
        </Badge>
      )}

      {/* ETA */}
      {summary.eta_seconds && summary.status === 'running' && (
        <Badge variant="outline">
          {t('health.eta')}: {Math.floor(summary.eta_seconds / 60)}m
        </Badge>
      )}

      {/* Blockers */}
      {summary.blockers.length > 0 && (
        <Badge variant="destructive">
          <AlertTriangle className="h-3 w-3 mr-1" />
          {summary.blockers.length} {t('health.blockers')}
        </Badge>
      )}
    </div>
  );
}
