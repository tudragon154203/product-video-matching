'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus } from '@/lib/zod/job'
import { jobApi, getPhaseInfo } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTranslations } from 'next-intl'
import Link from 'next/link'

const MOCK_JOBS = [
  {
    job_id: 'job-123',
    query: 'ergonomic pillows',
    phase: 'completed' as const,
    percent: 100,
    counts: { products: 50, videos: 120, images: 300, frames: 600 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
  {
    job_id: 'job-124', 
    query: 'standing desk',
    phase: 'matching' as const,
    percent: 80,
    counts: { products: 30, videos: 80, images: 200, frames: 400 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
  {
    job_id: 'job-125',
    query: 'gaming chair',
    phase: 'collection' as const,
    percent: 20,
    counts: { products: 10, videos: 25, images: 50, frames: 100 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
]

interface JobStats {
  totalJobs: number
  runningJobs: number
  completedJobs: number
  failedJobs: number
}

export function JobSidebar() {
  const t = useTranslations('jobs')
  const [stats, setStats] = useState<JobStats>({
    totalJobs: 0,
    runningJobs: 0,
    completedJobs: 0,
    failedJobs: 0,
  })

  const { data: recentJobs } = useQuery({
    queryKey: ['job-stats'],
    queryFn: async () => {
      // For this sprint, we'll use mock data since we don't have a backend endpoint
      return MOCK_JOBS
    },
    initialData: MOCK_JOBS,
  })

  useEffect(() => {
    if (recentJobs) {
      const running = (recentJobs as any[]).filter(job => 
        job.phase === 'collection' || job.phase === 'feature_extraction' || job.phase === 'matching' || job.phase === 'evidence'
      ).length
      
      const completed = (recentJobs as any[]).filter(job => job.phase === 'completed').length
      const failed = (recentJobs as any[]).filter(job => job.phase === 'failed').length
      
      setStats({
        totalJobs: recentJobs.length,
        runningJobs: running,
        completedJobs: completed,
        failedJobs: failed,
      })
    }
  }, [recentJobs])

  const sortedJobs = [...(recentJobs as any[])].sort((a, b) => 
    new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()
  )

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      {/* Job Stats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">{t('jobs')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('total')}</span>
            <Badge variant="secondary">{stats.totalJobs}</Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('running')}</span>
            <Badge variant="default" className="bg-yellow-500 text-yellow-50">
              {stats.runningJobs}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('completed')}</span>
            <Badge variant="default" className="bg-green-500 text-green-50">
              {stats.completedJobs}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('failed')}</span>
            <Badge variant="destructive">
              {stats.failedJobs}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Job List */}
      <Card className="flex-1 overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">{t('history')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 overflow-y-auto max-h-96">
          {sortedJobs.map((job) => {
            const phaseInfo = getPhaseInfo(job.phase)
            return (
              <Link 
                key={job.job_id} 
                href={`/jobs/${job.job_id}`}
                className="block p-3 rounded-lg border hover:bg-accent/50 transition-colors"
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
                      <span className="text-xs text-muted-foreground">
                        {job.percent}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{formatToGMT7(job.updated_at)}</span>
                    <span>{phaseInfo.label}</span>
                  </div>
                </div>
              </Link>
            )
          })}
          
          {sortedJobs.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-sm">{t('noRecentJobs')}</p>
              <div className="mt-2">
                <Link href="/">
                  <Button variant="outline" size="sm" className="w-full">{t('navigation.goHome')}</Button>
                </Link>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}