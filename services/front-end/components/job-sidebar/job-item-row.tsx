'use client'

import { JobItem } from '@/lib/zod/job'
import { getPhaseInfo } from '@/lib/api/utils/phase'
import type { Phase } from '@/lib/zod/job'
import { formatToGMT7 } from '@/lib/time'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling'

interface JobItemRowProps {
  job: JobItem
}

export function JobItemRow({ job }: JobItemRowProps) {
  const { phase: currentPhase, percent, counts } = useJobStatusPolling(job.job_id);
  const phaseInfo = getPhaseInfo(currentPhase as Phase);
  const displayDate = job.updated_at || job.created_at;

  // Determine if products/videos are done for collection phase
  const productsDone = counts?.products > 0; // Safely handle undefined counts
  const videosDone = counts?.videos > 0; // Safely handle undefined counts
  const collectionFinished = currentPhase === 'collection' && productsDone && videosDone;


  return (
    <Link
      key={job.job_id}
      href={`/jobs/${job.job_id}`}
      className="block p-3 rounded-lg border hover:bg-accent/50 transition-colors mb-2"
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm truncate">{job.query}</h4>
          <div className="flex items-center space-x-2" aria-live="polite" role="status">
            {phaseInfo && (
              <>
                <div
                  data-testid="status-color-circle" className={`h-2 w-2 rounded-full ${phaseInfo.color === 'blue' ? 'bg-blue-500' :
                      phaseInfo.color === 'yellow' ? 'bg-yellow-500' :
                        phaseInfo.color === 'purple' ? 'bg-purple-500' :
                          phaseInfo.color === 'orange' ? 'bg-orange-500' :
                            phaseInfo.color === 'green' ? 'bg-green-500' :
                              phaseInfo.color === 'red' ? 'bg-red-500' :
                                'bg-gray-500'
                    }`}
                />
                <span className="text-xs text-muted-foreground">
                  {phaseInfo.label.replace('…', '')}
                </span>
              </>
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