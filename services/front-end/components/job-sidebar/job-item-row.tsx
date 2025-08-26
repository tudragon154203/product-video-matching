'use client'

import { JobItem } from '@/lib/zod/job'
import { getPhaseInfo } from '@/lib/api/utils/phase'
import type { Phase } from '@/lib/zod/job'
import { formatToGMT7 } from '@/lib/time'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

interface JobItemRowProps {
  job: JobItem
}

export function JobItemRow({ job }: JobItemRowProps) {
  const phaseInfo = getPhaseInfo(job.phase as Phase)
  const displayDate = job.updated_at || job.created_at
  
  return (
    <Link 
      key={job.job_id} 
      href={`/jobs/${job.job_id}`}
      className="block p-3 rounded-lg border hover:bg-accent/50 transition-colors mb-2"
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm truncate">{job.query}</h4>
          <div className="flex items-center space-x-1">
            <div
              className={`h-2 w-2 rounded-full ${
                job.phase === 'completed'
                  ? 'bg-green-500'
                  : job.phase === 'failed'
                  ? 'bg-red-500'
                  : 'bg-yellow-500'
              }`}
            />
            <Badge variant="secondary" className="text-xs">
              {phaseInfo.label}
            </Badge>
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