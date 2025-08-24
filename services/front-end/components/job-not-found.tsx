'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Link } from 'next/link'

interface JobNotFoundProps {
  jobId: string
}

export function JobNotFound({ jobId }: JobNotFoundProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Job Not Found</CardTitle>
        <CardDescription>
          The job you're looking for doesn't exist or hasn't started yet.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Job ID: {jobId}
          </p>
          <div className="flex space-x-2">
            <Button asChild>
              <Link href="/jobs">Browse All Jobs</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/">Go Home</Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}