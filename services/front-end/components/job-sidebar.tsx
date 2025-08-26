'use client'

import { useQuery } from '@tanstack/react-query'
import { JobListResponse, JobItem } from '@/lib/zod/job'
import { jobApiService } from '@/lib/api/services/job.api'
import { JobStatsCard } from '@/components/job-sidebar/job-stats-card'
import { JobListCard } from '@/components/job-sidebar/job-list-card'
import { useJobStats, useGroupedJobs, useSortedJobs } from '@/components/job-sidebar/hooks'

export function JobSidebar() {
  // Fetch jobs using real API
  const { data: jobsResponse, isLoading, error } = useQuery<JobListResponse>({
    queryKey: ['jobs-list'],
    queryFn: async () => {
      return await jobApiService.listJobs({ limit: 100 })
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const jobs = jobsResponse?.items || []
  const stats = useJobStats(jobs)
  const sortedJobs = useSortedJobs(jobs)
  const groupedJobs = useGroupedJobs(sortedJobs)

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      <JobStatsCard stats={stats} isLoading={isLoading} />
      <JobListCard 
        jobs={sortedJobs} 
        groupedJobs={groupedJobs} 
        isLoading={isLoading} 
        error={error ?? null} 
      />
    </div>
  )
}