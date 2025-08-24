'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Link from 'next/link'
import { useTranslations } from 'next-intl'

interface JobNotFoundProps {
  jobId: string
}

export function JobNotFound({ jobId }: JobNotFoundProps) {
  const t = useTranslations('jobs')
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('jobNotFound')}</CardTitle>
        <CardDescription>
          {t('jobNotFoundDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Job ID: {jobId}
          </p>
          <div className="flex space-x-2">
            <Link href="/jobs">
              <Button className="flex-1">{t('browseAllJobs')}</Button>
            </Link>
            <Link href="/">
              <Button variant="outline" className="flex-1">{t('navigation.goHome')}</Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}