import { useMemo } from 'react'
import { JobItem } from '@/lib/zod/job'
import { JobStats, GroupedJobs } from '@/components/job-sidebar/types'
import { getTimeCategory } from '@/components/job-sidebar/time-utils'

// Custom hook for job statistics calculation
export function useJobStats(jobs: JobItem[]): JobStats {
  return useMemo(() => {
    if (jobs.length === 0) {
      return {
        totalJobs: 0,
        runningJobs: 0,
        completedJobs: 0,
        failedJobs: 0,
      }
    }

    const running = jobs.filter(job => 
      job.phase === 'collection' || 
      job.phase === 'feature_extraction' || 
      job.phase === 'matching' || 
      job.phase === 'evidence'
    ).length
    
    const completed = jobs.filter(job => job.phase === 'completed').length
    const failed = jobs.filter(job => job.phase === 'failed').length
    
    return {
      totalJobs: jobs.length,
      runningJobs: running,
      completedJobs: completed,
      failedJobs: failed,
    }
  }, [jobs])
}

// Custom hook for grouping jobs by time
export function useGroupedJobs(jobs: JobItem[]): GroupedJobs {
  return useMemo(() => {
    const groups: GroupedJobs = {
      today: [],
      yesterday: [],
      last7Days: [],
      lastMonth: [],
      older: []
    }
    
    jobs.forEach(job => {
      const category = getTimeCategory(job.updated_at)
      groups[category].push(job)
    })
    
    return groups
  }, [jobs])
}

// Custom hook for sorting jobs
export function useSortedJobs(jobs: JobItem[]) {
  return useMemo(() => {
    return [...jobs].sort((a, b) => {
      const aDate = a.updated_at ? new Date(a.updated_at).getTime() : new Date(a.created_at).getTime()
      const bDate = b.updated_at ? new Date(b.updated_at).getTime() : new Date(b.created_at).getTime()
      return bDate - aDate
    })
  }, [jobs])
}