'use client'

import Link from 'next/link'

import { Badge } from '@/components/ui/badge'
import { getPhaseInfo, phaseInfo as phaseInfoMap } from '@/lib/api/utils/phase'
import type { JobItem, Phase } from '@/lib/zod/job'
import { formatToGMT7 } from '@/lib/time'
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling'

interface JobItemRowProps {
  job: JobItem
}

const KNOWN_PHASES = Object.keys(phaseInfoMap) as Phase[]

const isKnownPhase = (value: string | undefined): value is Phase =>
  !!value && (KNOWN_PHASES as readonly string[]).includes(value)

const clampPercent = (percent?: number) => {
  if (percent === undefined || Number.isNaN(percent)) {
    return 0
  }

  return Math.min(100, Math.max(0, Math.round(percent)))
}

const resolveColorClass = (color: string) =>
  color.startsWith('bg-') ? color : `bg-${color}-500`

export function JobItemRow({ job }: JobItemRowProps) {
  const {
    phase: livePhase,
    percent,
    isCollecting,
    counts,
    collection,
  } = useJobStatusPolling(job.job_id)

  const resolvedPhase: Phase = isKnownPhase(livePhase)
    ? livePhase
    : isKnownPhase(job.phase)
      ? (job.phase as Phase)
      : 'unknown'

  const phaseInfo = getPhaseInfo(resolvedPhase)
  const colorClass = resolveColorClass(phaseInfo.color)
  const displayDate = job.updated_at || job.created_at

  const shouldShowStatusCircle = resolvedPhase !== 'collection'

  const renderPhaseEffect = () => {
    if (resolvedPhase === 'collection' || !phaseInfo.effect || phaseInfo.effect === 'none') {
      return null
    }

    switch (phaseInfo.effect) {
      case 'spinner':
        return (
          <div
            data-testid="status-spinner"
            className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
            aria-hidden="true"
          />
        )
      case 'progress-bar':
        return (
          <div data-testid="status-progress-bar" className="w-16" aria-hidden="true">
            <div className="h-1 w-full rounded-full bg-muted">
              <div
                className={`h-1 rounded-full ${colorClass}`}
                style={{ width: `${clampPercent(percent)}%` }}
              />
            </div>
          </div>
        )
      case 'animated-dots':
        return (
          <div data-testid="status-animated-dots" className="flex items-center space-x-1 text-xs text-muted-foreground" aria-hidden="true">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" style={{ animationDelay: '0.2s' }} />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" style={{ animationDelay: '0.4s' }} />
          </div>
        )
      default:
        return null
    }
  }

  const renderCollectionSummary = () => {
    if (resolvedPhase !== 'collection' || !collection) {
      return null
    }

    const messages: string[] = []

    if (collection.products_done) {
      messages.push('✔ Products done')
    }

    if (collection.videos_done) {
      messages.push('✔ Videos done')
    }

    if (collection.products_done && collection.videos_done) {
      messages.push('Collection finished')
    }

    if (messages.length === 0) {
      return null
    }

    return (
      <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground" aria-live="polite">
        {messages.map((message) => (
          <Badge key={message} variant="outline" className="border-dashed text-xs">
            {message}
          </Badge>
        ))}
      </div>
    )
  }

  return (
    <Link
      key={job.job_id}
      href={`/jobs/${job.job_id}`}
      className="block rounded-lg border p-3 transition-colors hover:bg-accent/50"
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="truncate text-sm font-medium">{job.query}</h4>
          <div className="flex items-center space-x-2" aria-live="polite" role="status">
            {shouldShowStatusCircle && (
              <div
                data-testid="status-color-circle"
                className={`h-2 w-2 rounded-full ${colorClass}`}
              />
            )}
            <span className="text-xs text-muted-foreground">{phaseInfo.label}</span>
            {renderPhaseEffect()}
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatToGMT7(displayDate)}</span>
          <span className="capitalize">{job.industry}</span>
        </div>
        {resolvedPhase !== 'collection' && percent !== undefined && !Number.isNaN(percent) && (
          <div className="flex items-center space-x-1 text-xs text-muted-foreground" aria-live="polite">
            <span>Progress:</span>
            <span className="font-medium">{clampPercent(percent)}%</span>
          </div>
        )}
        {resolvedPhase !== 'collection' && counts && (
          <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-muted-foreground" aria-hidden="true">
            <span>Products: {counts.products}</span>
            <span>Videos: {counts.videos}</span>
            <span>Images: {counts.images}</span>
            <span>Frames: {counts.frames}</span>
          </div>
        )}
        {!isCollecting && renderCollectionSummary()}
      </div>
    </Link>
  )
}
