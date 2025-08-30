'use client'

import { useQuery } from '@tanstack/react-query'
import { JobListResponse, JobItem } from '@/lib/zod/job'
import { jobApiService } from '@/lib/api/services/job.api'
import { getPollingInterval } from '@/lib/config/pagination'
import { JobStatsCard } from './job-sidebar/job-stats-card'
import { JobListCard } from './job-sidebar/job-list-card'
import { StartNewJobButton } from './job-sidebar/start-new-job-button'
import { useJobStats, useGroupedJobs, useSortedJobs } from './job-sidebar/hooks'

export function JobSidebar() {
  // Fetch jobs using real API with reduced polling frequency
  const { data: jobsResponse, isLoading, error } = useQuery<JobListResponse>({
    queryKey: ['jobs-list'],
    queryFn: async () => {
      return await jobApiService.listJobs({ limit: 100 })
    },
    refetchInterval: getPollingInterval('jobSidebar'), // Use centralized config
    refetchOnWindowFocus: true, // Refetch when window regains focus
    refetchOnReconnect: true, // Refetch on network reconnect
  })

  const jobs = jobsResponse?.items || []
  const stats = useJobStats(jobs)
  const sortedJobs = useSortedJobs(jobs)
  const groupedJobs = useGroupedJobs(sortedJobs)

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      <JobStatsCard stats={stats} isLoading={isLoading} />
      <StartNewJobButton />
      <JobListCard
        jobs={sortedJobs}
        groupedJobs={groupedJobs}
        isLoading={isLoading}
        error={error ?? null}
      />
    </div>
  )
}