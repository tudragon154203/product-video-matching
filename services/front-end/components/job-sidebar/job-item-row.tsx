'use client'

import { JobItem } from '@/lib/zod/job'
import { getPhaseInfo } from '@/lib/api/utils/phase'
import type { Phase } from '@/lib/zod/job'
import { formatToGMT7 } from '@/lib/time'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling';

interface JobItemRowProps {
  job: JobItem
}

export function JobItemRow({ job }: JobItemRowProps) {
  const { phase: currentPhase, percent, counts } = useJobStatusPolling(job.job_id);
  const phaseInfo = getPhaseInfo(currentPhase as Phase);
  const displayDate = job.updated_at || job.created_at;

  // Determine if products/videos are done for collection phase
  const productsDone = counts.products > 0;
  const videosDone = counts.videos > 0;
  const collectionFinished = currentPhase === 'collection' && productsDone && videosDone;

  // Phase-specific effects
  const renderPhaseEffect = () => {
    switch (phaseInfo.effect) {
      case 'spinner':
        return (
          <div data-testid="status-spinner" className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-900"></div>
        );
      case 'progress-bar':
        return (
          <div data-testid="status-progress-bar" className="w-3 h-3">
            <div className="animate-pulse h-1 w-full bg-current rounded"></div>
          </div>
        );
      case 'animated-dots':
        return (
          <div data-testid="status-animated-dots" className="flex space-x-1">
            <div className="h-1 w-1 bg-current rounded-full animate-bounce"></div>
            <div className="h-1 w-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="h-1 w-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Link
      key={job.job_id}
      href={`/jobs/${job.job_id}`}
      className="block p-3 rounded-lg border hover:bg-accent/50 transition-colors mb-2"
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm truncate">{job.query}</h4>
          <div className="flex items-center space-x-1" aria-live="polite" role="status">
            {/* Phase-specific effects */}
            {currentPhase !== 'unknown' && currentPhase !== 'completed' && currentPhase !== 'failed' && renderPhaseEffect()}
            <div
              data-testid="status-color-circle" className={`h-2 w-2 rounded-full bg-${phaseInfo.color}-500`}
            />
            <Badge variant="secondary" className="text-xs">
              {phaseInfo.label}
            </Badge>
            {/* Collection phase badges */}
            {currentPhase === 'collection' && productsDone && (
              <Badge variant="outline" className="text-xs">✔ Products done</Badge>
            )}
            {currentPhase === 'collection' && videosDone && (
              <Badge variant="outline" className="text-xs">✔ Videos done</Badge>
            )}
            {collectionFinished && (
              <Badge variant="default" className="text-xs">Collection finished</Badge>
            )}
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatToGMT7(displayDate)}</span>
          <span className="capitalize">{job.industry}</span>
        </div>
      </div>
    </Link>
  )
}