'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useTranslations } from 'next-intl'
import { JobStats } from '@/components/job-sidebar/types'

interface JobStatsCardProps {
  stats: JobStats
  isLoading: boolean
}

export function JobStatsCard({ stats, isLoading }: JobStatsCardProps) {
  const t = useTranslations('jobs')

  return (
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
  )
}