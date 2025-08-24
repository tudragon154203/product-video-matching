import { JobStatsCard } from '@/components/job-stats-card'
import { StartJobForm } from '@/components/start-job-form'
import { JobStatusCard } from '@/components/job-status-card'

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="flex flex-col gap-4 py-4">
          <h1 className="text-3xl font-bold tracking-tight">Product Video Matching</h1>
          <p className="text-muted-foreground">
            Monitor and manage your product video matching jobs
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <JobStatsCard />
          <StartJobForm />
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4">Recent Jobs</h2>
          <JobStatusCard />
        </div>
      </div>
    </div>
  )
}