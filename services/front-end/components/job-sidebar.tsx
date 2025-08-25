'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobListResponse, JobItem } from '@/lib/zod/job'
import { jobApiService } from '@/lib/api/services/job.api'
import { getPhaseInfo } from '@/lib/api/utils/phase'
import { formatToGMT7 } from '@/lib/time'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTranslations } from 'next-intl'
import Link from 'next/link'

interface JobStats {
  totalJobs: number
  runningJobs: number
  completedJobs: number
  failedJobs: number
}

interface GroupedJobs {
  today: JobItem[]
  yesterday: JobItem[]
  last7Days: JobItem[]
  lastMonth: JobItem[]
  older: JobItem[]
}

function getTimeCategory(dateString: string | null): keyof GroupedJobs {
  if (!dateString) return 'older'
  
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

function groupJobsByTime(jobs: JobItem[]): GroupedJobs {
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

  // Fetch jobs using real API
  const { data: jobsResponse, isLoading, error } = useQuery({
    queryKey: ['jobs-list'],
    queryFn: async () => {
      return await jobApiService.listJobs({ limit: 100 })
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const jobs = jobsResponse?.items || []

  useEffect(() => {
    if (jobs.length > 0) {
      const running = jobs.filter(job => 
        job.phase === 'collection' || 
        job.phase === 'feature_extraction' || 
        job.phase === 'matching' || 
        job.phase === 'evidence'
      ).length
      
      const completed = jobs.filter(job => job.phase === 'completed').length
      const failed = jobs.filter(job => job.phase === 'failed').length
      
      setStats({
        totalJobs: jobs.length,
        runningJobs: running,
        completedJobs: completed,
        failedJobs: failed,
      })
    }
  }, [jobs])

  const sortedJobs = [...jobs].sort((a, b) => {
    const aDate = a.updated_at ? new Date(a.updated_at).getTime() : new Date(a.created_at).getTime()
    const bDate = b.updated_at ? new Date(b.updated_at).getTime() : new Date(b.created_at).getTime()
    return bDate - aDate
  })
  
  const groupedJobs = groupJobsByTime(sortedJobs)

  const renderJobGroup = (jobs: JobItem[], groupKey: keyof GroupedJobs) => {
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
            <Badge variant="secondary">
              {isLoading ? '...' : stats.totalJobs}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('running')}</span>
            <Badge variant="default" className="bg-yellow-500 text-yellow-50">
              {isLoading ? '...' : stats.runningJobs}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('completed')}</span>
            <Badge variant="default" className="bg-green-500 text-green-50">
              {isLoading ? '...' : stats.completedJobs}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{t('failed')}</span>
            <Badge variant="destructive">
              {isLoading ? '...' : stats.failedJobs}
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
          {isLoading && (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-sm">{t('loadingJobs')}</p>
            </div>
          )}
          
          {error && (
            <div className="text-center py-8 text-red-500">
              <p className="text-sm">{t('failedToLoadJobsError')}</p>
            </div>
          )}
          
          {!isLoading && !error && (
            <>
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
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}