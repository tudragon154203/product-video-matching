import { StartJobForm } from '@/components/start-job-form'
import { JobHistoryList } from '@/components/job-history-list'

export default function JobsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="flex flex-col gap-4 py-4">
          <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>
          <p className="text-muted-foreground">
            Start new product video matching jobs and view job history
          </p>
        </div>

        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Start New Job</h2>
            <StartJobForm />
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-4">Job History</h2>
            <JobHistoryList />
          </div>
        </div>
      </div>
    </div>
  )
}