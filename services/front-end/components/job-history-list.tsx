'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus } from '@/lib/zod/job'
import { jobApi, getPhaseInfo } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useTranslations } from 'next-intl'

export function JobHistoryList() {
  const t = useTranslations('jobs')
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
          <p className="text-muted-foreground">{t('noJobHistory')}</p>
          <div className="mt-4">
            <Link href="/jobs">
              <Button className="w-full">{t('startFirstJob')}</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('jobHistory')}</CardTitle>
        <CardDescription>
          {t('jobHistoryDescription')}
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
                    {t('productsAndVideos', { 
                      products: job.counts.products, 
                      videos: job.counts.videos 
                    })}
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/jobs/${job.job_id}`}>
                      <Button variant="outline" size="sm">{t('viewDetails')}</Button>
                    </Link>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}