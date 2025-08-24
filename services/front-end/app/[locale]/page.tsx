import { StartJobForm } from '@/components/start-job-form'
import { getTranslations } from 'next-intl/server'

export default async function Home({ params }: { params: { locale: string } }) {
  const t = await getTranslations({ locale: params.locale, namespace: 'jobs' })

  return (
    <div className="w-full">
      <StartJobForm />
    </div>
  )
}