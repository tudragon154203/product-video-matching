'use client'

import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus } from '@/lib/zod/job'
import { jobApi, getPhaseInfo } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTranslations } from 'next-intl'
import Link from 'next/link'

// Generate mock jobs with relative timestamps
function generateMockJobs() {
  const now = new Date()
  
  // Helper function to create a date relative to now
  const getRelativeDate = (daysAgo: number, hoursAgo: number = 0) => {
    return new Date(now.getTime() - (daysAgo * 24 * 60 * 60 * 1000) - (hoursAgo * 60 * 60 * 1000)).toISOString()
  }
  
  return [
    // Today
    {
      job_id: 'job-today-1',
      query: 'ergonomic pillows',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 50, videos: 120, images: 300, frames: 600 },
      updated_at: getRelativeDate(0, 2), // 2 hours ago
    },
    {
      job_id: 'job-today-2',
      query: 'standing desk',
      phase: 'matching' as const,
      percent: 80,
      counts: { products: 30, videos: 80, images: 200, frames: 400 },
      updated_at: getRelativeDate(0, 5), // 5 hours ago
    },
    // Yesterday
    {
      job_id: 'job-yesterday-1',
      query: 'gaming chair',
      phase: 'collection' as const,
      percent: 20,
      counts: { products: 10, videos: 25, images: 50, frames: 100 },
      updated_at: getRelativeDate(1, 4), // 1 day and 4 hours ago
    },
    {
      job_id: 'job-yesterday-2',
      query: 'wireless headphones',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 25, videos: 60, images: 150, frames: 300 },
      updated_at: getRelativeDate(1, 10), // 1 day and 10 hours ago
    },
    // Last 7 days
    {
      job_id: 'job-week-1',
      query: 'laptop cooling pad',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 20, videos: 45, images: 100, frames: 200 },
      updated_at: getRelativeDate(3), // 3 days ago
    },
    {
      job_id: 'job-week-2',
      query: 'mechanical keyboard',
      phase: 'failed' as const,
      percent: 45,
      counts: { products: 15, videos: 30, images: 75, frames: 150 },
      updated_at: getRelativeDate(5), // 5 days ago
    },
    // Last month
    {
      job_id: 'job-month-1',
      query: 'smart watch',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 40, videos: 90, images: 200, frames: 400 },
      updated_at: getRelativeDate(15), // 15 days ago
    },
    {
      job_id: 'job-month-2',
      query: 'coffee maker',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 35, videos: 70, images: 180, frames: 350 },
      updated_at: getRelativeDate(20), // 20 days ago
    },
    // Older
    {
      job_id: 'job-old-1',
      query: 'bluetooth speaker',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 30, videos: 65, images: 160, frames: 320 },
      updated_at: getRelativeDate(45), // 45 days ago
    },
    {
      job_id: 'job-old-2',
      query: 'fitness tracker',
      phase: 'completed' as const,
      percent: 100,
      counts: { products: 28, videos: 55, images: 140, frames: 280 },
      updated_at: getRelativeDate(60), // 60 days ago
    },
  ]
}

interface JobStats {
  totalJobs: number
  runningJobs: number
  completedJobs: number
  failedJobs: number
}

interface GroupedJobs {
  today: any[]
  yesterday: any[]
  last7Days: any[]
  lastMonth: any[]
  older: any[]
}

function getTimeCategory(dateString: string): keyof GroupedJobs {
  const now = new Date()
  const date = new Date(dateString)
  
  // Reset time to compare only dates
  const nowDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const jobDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  
  const diffMs = nowDate.getTime() - jobDate.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) {
    return 'today'
  } else if (diffDays === 1) {
    return 'yesterday'
  } else if (diffDays <= 7) {
    return 'last7Days'
  } else if (diffDays <= 30) {
    return 'lastMonth'
  } else {
    return 'older'
  }
}

function groupJobsByTime(jobs: any[]): GroupedJobs {
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
}

function TimeSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center py-2 px-1">
      <div className="flex-1 h-px bg-gray-300"></div>
      <span className="px-3 text-xs text-gray-500 font-medium">{label}</span>
      <div className="flex-1 h-px bg-gray-300"></div>
    </div>
  )
}

export function JobSidebar() {
  const t = useTranslations('jobs')
  const [stats, setStats] = useState<JobStats>({
    totalJobs: 0,
    runningJobs: 0,
    completedJobs: 0,
    failedJobs: 0,
  })

  // Generate mock data on client side to avoid hydration issues
  const mockJobs = useMemo(() => generateMockJobs(), [])

  const { data: recentJobs } = useQuery({
    queryKey: ['job-stats'],
    queryFn: async () => {
      // For this sprint, we'll use mock data since we don't have a backend endpoint
      return mockJobs
    },
    initialData: mockJobs,
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
  
  const groupedJobs = groupJobsByTime(sortedJobs)

  const renderJobGroup = (jobs: any[], groupKey: keyof GroupedJobs) => {
    if (jobs.length === 0) return null
    
    const timeLabels = {
      today: t('today'),
      yesterday: t('yesterday'),
      last7Days: t('last7Days'),
      lastMonth: t('lastMonth'),
      older: t('older')
    }
    
    return (
      <div key={groupKey}>
        <TimeSeparator label={timeLabels[groupKey]} />
        {jobs.map((job) => {
          const phaseInfo = getPhaseInfo(job.phase)
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
      </div>
    )
  }

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
          {Object.keys(groupedJobs).map(groupKey => 
            renderJobGroup(groupedJobs[groupKey as keyof GroupedJobs], groupKey as keyof GroupedJobs)
          )}
          
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