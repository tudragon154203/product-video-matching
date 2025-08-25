import { StartJobForm } from '@/components/start-job-form'
import { useTranslations } from 'next-intl'

export default function JobsPage() {
  const t = useTranslations('jobs')
  const tNav = useTranslations('navigation')
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="flex flex-col gap-4 py-4">
          <h1 className="text-3xl font-bold tracking-tight">{tNav('jobs')}</h1>
          <p className="text-muted-foreground">
            {t('startNewDescription')}
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">{t('startNew')}</h2>
            <StartJobForm />
          </div>

        </div>
      </div>
    </div>
  )
}