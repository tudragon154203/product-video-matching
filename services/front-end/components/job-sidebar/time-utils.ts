import { GroupedJobs } from '@/components/job-sidebar/types'

export function getTimeCategory(dateString: string | null): keyof GroupedJobs {
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

export function groupJobsByTime(jobs: any[]): GroupedJobs {
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