'use client'

import { getPhaseInfo } from '@/lib/api/utils/phase'
import type { Phase } from '@/lib/zod/job'
import { Badge } from '@/components/ui/badge'
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

interface JobStatusHeaderProps {
  jobId: string;
  isCollecting?: boolean;
}

export function JobStatusHeader({ jobId, isCollecting = false }: JobStatusHeaderProps) {
  const { phase: currentPhase, percent } = useJobStatusPolling(jobId);
  const phaseInfo = getPhaseInfo(currentPhase as Phase);
  const colorClass = phaseInfo.color.startsWith('bg-')
    ? phaseInfo.color
    : `bg-${phaseInfo.color}-500`;
  const { parentRef: headerRef } = useAutoAnimateList<HTMLDivElement>()

  // Phase-specific effects
  const renderPhaseEffect = () => {
    if (!phaseInfo || !phaseInfo.effect || phaseInfo.effect === 'none') {
      return null;
    }

    switch (phaseInfo.effect) {
      case 'spinner':
        return (
          <div data-testid="status-spinner" className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-900"></div>
        );
      case 'progress-bar':
        return (
          <div data-testid="status-progress-bar" className="w-3 h-3">
            <div className="animate-pulse h-1 w-full bg-current rounded"></div>
          </div>
        );
      case 'animated-dots':
        return (
          <div data-testid="status-animated-dots" className="flex space-x-1">
            <div className="h-1 w-1 bg-current rounded-full animate-bounce"></div>
            <div className="h-1 w-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="h-1 w-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
        );
      default:
        return null;
    }
  };

  if (!phaseInfo) {
    return null;
  }

  return (
    <div className="flex items-center space-x-4 py-4 border-b" ref={headerRef}>
      <div className="flex items-center space-x-2">
        {/* Phase-specific effects */}
        {isCollecting && renderPhaseEffect()}
        <div
          data-testid="status-color-circle" className={`h-4 w-4 rounded-full ${colorClass}`}
        />
        <Badge variant="secondary" className="text-xs">
          {phaseInfo.label}
        </Badge>
      </div>

      {percent !== undefined && (
        <div className="flex items-center space-x-1 text-sm text-muted-foreground">
          <span>Progress:</span>
          <span className="font-medium">{percent}%</span>
        </div>
      )}
    </div>
  );
}
