import React from 'react';
import { cn } from '@/lib/utils';

interface JobSplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
  className?: string;
}

export function JobSplitView({ left, right, className = '' }: JobSplitViewProps) {
  return (
    <div className={cn(
      "w-full",
      "grid grid-cols-1 lg:grid-cols-2",
      "gap-6",
      className
    )}>
      <div className="space-y-4">
        {left}
      </div>
      <div className="space-y-4">
        {right}
      </div>
    </div>
  );
}