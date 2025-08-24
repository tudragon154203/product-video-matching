'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus, Phase } from '@/lib/zod/job'
import { jobApi, getPhaseInfo } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useTranslations, useLocale } from 'next-intl'

const RECENT_JOBS_LIMIT = 5

interface JobStatusCardProps {
  jobId?: string
}

export function JobStatusCard({ jobId }: JobStatusCardProps = {}) {
  const [limit] = useState(RECENT_JOBS_LIMIT)
  const t = useTranslations('jobs')
  const tCommon = useTranslations('common')

  const { data: jobs, isLoading, error } = useQuery({
    queryKey: ['recent-jobs', limit],
    queryFn: async () => {
      // For this mock implementation, we'll return mock data
      // In a real implementation, you would have an endpoint to get recent jobs
      return []
    },
    initialData: [],
  })

  if (jobId) {
    // Show specific job status when jobId is provided
    const { data: jobStatus, isLoading: isJobLoading, error: jobError } = useQuery({
      queryKey: ['job', jobId],
      queryFn: () => jobApi.getJobStatus(jobId),
    })

    if (isJobLoading) {
      return <Card><CardContent><p>{tCommon('loading')}</p></CardContent></Card>
    }

    if (jobError) {
      return <Card><CardContent><p className="text-red-500">{tCommon('error')} loading job status</p></CardContent></Card>
    }

    if (!jobStatus || jobStatus.phase === 'unknown') {
      return (
        <Card>
          <CardHeader>
            <CardTitle>{t('jobNotFound')}</CardTitle>
            <CardDescription>
              {t('jobNotFoundDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div>
              <Link href="/jobs">
                <Button className="w-full">{t('browseAllJobs')}</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )
    }

    const phaseInfo = getPhaseInfo(jobStatus.phase)

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            {t('jobStatus')}
            <div className="flex items-center space-x-2">
              <div
                className={`h-3 w-3 rounded-full ${
                  jobStatus.phase === 'completed'
                    ? 'bg-green-500'
                    : jobStatus.phase === 'failed'
                    ? 'bg-red-500'
                    : 'bg-yellow-500'
                }`}
              />
              <span className="text-sm">{phaseInfo.label}</span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{jobStatus.counts.products}</div>
              <div className="text-sm text-muted-foreground">{t('products')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{jobStatus.counts.videos}</div>
              <div className="text-sm text-muted-foreground">{t('videos')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{jobStatus.counts.images}</div>
              <div className="text-sm text-muted-foreground">{t('images')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{jobStatus.counts.frames}</div>
              <div className="text-sm text-muted-foreground">{t('frames')}</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t('progress')}</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${jobStatus.percent}%` }}
              />
            </div>
            <div className="text-sm text-right">{jobStatus.percent}%</div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t('lastUpdated')}</div>
            <div className="text-sm text-muted-foreground">
              {formatToGMT7(jobStatus.updated_at)}
            </div>
          </div>

          <div className="mt-4">
            <Link href={`/jobs/${jobId}`}>
              <Button className="w-full">{t('viewFullDetails')}</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Show recent jobs list when no jobId is provided
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('recentJobs')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>{tCommon('loading')} recent jobs...</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('recentJobs')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">{t('failedToLoadJobs')}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('recentJobs')}</CardTitle>
      </CardHeader>
      <CardContent>
        {jobs.length === 0 ? (
          <p className="text-muted-foreground">{t('noRecentJobs')}</p>
        ) : (
          <div className="space-y-4">
            {jobs.map((job: JobStatus) => (
              <div key={job.job_id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{job.job_id}</span>
                  <span className="text-sm text-muted-foreground">
                    {getPhaseInfo(job.phase).label}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">{t('percentComplete', { percent: job.percent })}</span>
                  <Link href={`/jobs/${job.job_id}`}>
                    <Button variant="outline" size="sm">{tCommon('view')}</Button>
                  </Link>
                </div>
              </div>
            ))}
            <div className="mt-4">
            <Link href="/jobs">
              <Button variant="outline" className="w-full">{t('browseAllJobs')}</Button>
            </Link>
          </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}