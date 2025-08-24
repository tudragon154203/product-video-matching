'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus } from '@/lib/zod/job'
import { jobApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTranslations } from 'next-intl'

const MOCK_JOBS = [
  {
    job_id: 'job-123',
    phase: 'completed' as const,
    percent: 100,
    counts: { products: 50, videos: 120, images: 300, frames: 600 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
  {
    job_id: 'job-124', 
    phase: 'matching' as const,
    percent: 80,
    counts: { products: 30, videos: 80, images: 200, frames: 400 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
  {
    job_id: 'job-125',
    phase: 'collection' as const,
    percent: 20,
    counts: { products: 10, videos: 25, images: 50, frames: 100 },
    updated_at: '2025-08-24T09:03:59.000Z',
  },
]

export function JobStatsCard() {
  const t = useTranslations('jobs')
  const [stats, setStats] = useState({
    totalJobs: 0,
    runningJobs: 0,
    completedJobs: 0,
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
      setStats({
        totalJobs: recentJobs.length,
        runningJobs: (recentJobs as any[]).filter(job => 
          job.phase === 'collection' || job.phase === 'feature_extraction' || job.phase === 'matching' || job.phase === 'evidence'
        ).length,
        completedJobs: (recentJobs as any[]).filter(job => job.phase === 'completed').length,
      })
    }
  }, [recentJobs])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('recentJobs')}</CardTitle>
        <CardDescription>
          {t('subtitle')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{stats.totalJobs}</div>
            <div className="text-sm text-muted-foreground">{t('recentJobs')}</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-600">{stats.runningJobs}</div>
            <div className="text-sm text-muted-foreground">{t('running')}</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{stats.completedJobs}</div>
            <div className="text-sm text-muted-foreground">{t('completed')}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}