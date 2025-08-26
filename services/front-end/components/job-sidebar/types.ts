import { JobItem } from '@/lib/zod/job'

export interface JobStats {
  totalJobs: number
  runningJobs: number
  completedJobs: number
  failedJobs: number
}

export interface GroupedJobs {
  today: JobItem[]
  yesterday: JobItem[]
  last7Days: JobItem[]
  lastMonth: JobItem[]
  older: JobItem[]
}