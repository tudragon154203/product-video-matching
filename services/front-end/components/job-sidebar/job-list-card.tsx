'use client'

import { useMemo } from 'react'
import { JobItem } from '@/lib/zod/job'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { JobItemRow } from '@/components/jobs/JobItemRow'
import { TimeSeparator } from '@/components/job-sidebar/time-separator'
import { GroupedJobs } from '@/components/job-sidebar/types'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

interface JobListCardProps {
  jobs: JobItem[]
  groupedJobs: GroupedJobs
  isLoading: boolean
  error: Error | null
}

export function JobListCard({ jobs = [], groupedJobs = {} as GroupedJobs, isLoading, error }: JobListCardProps) {
  const t = useTranslations('jobs')
  const tNav = useTranslations('navigation')

  // Animation hook for smooth job list transitions
  const { parentRef: jobsListRef } = useAutoAnimateList<HTMLDivElement>()

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
        {jobs.map((job) => (
          <JobItemRow key={job.job_id} job={job} />
        ))}
      </div>
    )
  }

  return (
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
            <div ref={jobsListRef}>
              {Object.keys(groupedJobs).map(groupKey =>
                renderJobGroup(groupedJobs[groupKey as keyof GroupedJobs], groupKey as keyof GroupedJobs)
              )}
            </div>

            {jobs.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p className="text-sm">{t('noRecentJobs')}</p>
                <div className="mt-2">
                  <Link href="/">
                    <Button variant="outline" size="sm" className="w-full">{tNav('goHome')}</Button>
                  </Link>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}