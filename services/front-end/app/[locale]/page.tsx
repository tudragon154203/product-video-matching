import { JobStatsCard } from '@/components/job-stats-card'
import { StartJobForm } from '@/components/start-job-form'
import { JobStatusCard } from '@/components/job-status-card'
import { useTranslations } from 'next-intl'

export default function Home() {
  const t = useTranslations('jobs')

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 py-4">
        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="text-muted-foreground">
          {t('subtitle')}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <JobStatsCard />
        <StartJobForm />
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">{t('recentJobs')}</h2>
        <JobStatusCard />
      </div>
    </div>
  )
}