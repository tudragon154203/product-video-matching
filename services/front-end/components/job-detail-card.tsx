'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { JobStatus, Phase } from '@/lib/zod/job'
import { jobApi, getPhaseInfo, shouldPoll } from '@/lib/api'
import { formatToGMT7 } from '@/lib/time'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { toast } from '@/components/ui/use-toast'
'use client'

import dynamic from 'next/dynamic'

const Link = dynamic(() => import('next/link').then(mod => mod.Link), { ssr: false })

interface JobDetailCardProps {
  jobId: string
}

export function JobDetailCard({ jobId }: JobDetailCardProps) {
  const [isPolling, setIsPolling] = useState(true)

  const { data: jobStatus, error, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobApi.getJobStatus(jobId),
    refetchInterval: (data) => {
      if (!shouldPoll(data?.phase)) {
        return false
      }
      return 5000 // Poll every 5 seconds
    },
  })

  useEffect(() => {
    if (jobStatus && !shouldPoll(jobStatus.phase)) {
      setIsPolling(false)
      if (jobStatus.phase === 'failed') {
        toast({
          title: 'Job Failed',
          description: 'The job encountered an error during execution.',
          variant: 'destructive',
        })
      }
    }
  }, [jobStatus, toast])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Loading Job Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Fetching job information...</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error Loading Job</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">
            {error instanceof Error ? error.message : 'Failed to load job status'}
          </p>
          <Button asChild className="mt-4">
            <Link href="/jobs">Back to Jobs</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (!jobStatus || jobStatus.phase === 'unknown') {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Job Not Found</CardTitle>
          <CardDescription>
            The job you're looking for doesn't exist or hasn't started yet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/jobs">Browse All Jobs</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  const phaseInfo = getPhaseInfo(jobStatus.phase)
  const progress = jobStatus.percent

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Job Status</CardTitle>
            <CardDescription>
              Job ID: {jobId}
              {isPolling && (
                <span className="ml-2 text-yellow-600 animate-pulse">
                  (Polling...)
                </span>
              )}
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <div
              className={`h-3 w-3 rounded-full ${
                jobStatus.phase === 'completed'
                  ? 'bg-green-500'
                  : jobStatus.phase === 'failed'
                  ? 'bg-red-500'
                  : 'bg-yellow-500'
              }`}
            />
            <span className="text-sm font-medium">{phaseInfo.label}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{jobStatus.counts.products}</div>
            <div className="text-sm text-muted-foreground">Products</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{jobStatus.counts.videos}</div>
            <div className="text-sm text-muted-foreground">Videos</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{jobStatus.counts.images}</div>
            <div className="text-sm text-muted-foreground">Images</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{jobStatus.counts.frames}</div>
            <div className="text-sm text-muted-foreground">Frames</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">Last Updated</div>
          <div className="text-sm text-muted-foreground">
            {formatToGMT7(jobStatus.updated_at)}
          </div>
        </div>

        <div className="flex justify-between">
          <Button variant="outline" asChild>
            <Link href="/jobs">Back to Jobs</Link>
          </Button>
          <Button asChild>
            <Link href={`/jobs/${jobId}`}>Refresh</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}