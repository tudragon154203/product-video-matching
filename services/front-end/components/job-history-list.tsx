'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus } from '@/lib/zod/job'
import { jobApi, getPhaseInfo } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Link } from 'next/link'

export function JobHistoryList() {
  const [jobs, setJobs] = useState<JobStatus[]>([])

  const { data } = useQuery({
    queryKey: ['job-history'],
    queryFn: async () => {
      // For this sprint, we'll use mock data since we don't have a backend endpoint
      return []
    },
    initialData: [],
  })

  useEffect(() => {
    if (data) {
      setJobs(data)
    }
  }, [data])

  const sortedJobs = [...jobs].sort((a, b) => 
    new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()
  )

  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <p className="text-muted-foreground">No job history available.</p>
          <Button asChild className="mt-4">
            <Link href="/jobs">Start Your First Job</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job History</CardTitle>
        <CardDescription>
          Your recently created and executed jobs
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sortedJobs.map((job) => {
            const phaseInfo = getPhaseInfo(job.phase)
            return (
              <div
                key={job.job_id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`h-3 w-3 rounded-full ${
                        job.phase === 'completed'
                          ? 'bg-green-500'
                          : job.phase === 'failed'
                          ? 'bg-red-500'
                          : 'bg-yellow-500'
                      }`}
                    />
                    <div>
                      <div className="font-medium">{job.job_id}</div>
                      <div className="text-sm text-muted-foreground">
                        {phaseInfo.label}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">{job.percent}%</div>
                    <div className="text-xs text-muted-foreground">
                      {formatToGMT7(job.updated_at)}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex justify-between items-center">
                  <div className="text-xs text-muted-foreground">
                    Products: {job.counts.products} | Videos: {job.counts.videos}
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/jobs/${job.job_id}`}>View Details</Link>
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}