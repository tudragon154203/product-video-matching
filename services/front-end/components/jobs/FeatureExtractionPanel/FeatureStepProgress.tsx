'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { useTranslations } from 'next-intl';

interface FeatureStepProgressProps {
  label: string;
  done: number;
  total: number;
  color: 'sky' | 'indigo' | 'pink';
  icon?: React.ReactNode;
}

export function FeatureStepProgress({ label, done, total, color, icon }: FeatureStepProgressProps) {
  const t = useTranslations('jobFeatureExtraction');
  
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  const status = percent >= 100 ? 'done' : percent > 0 ? 'active' : 'pending';
  
  const statusColors = {
    active: 'bg-yellow-100 text-yellow-900',
    done: 'bg-emerald-100 text-emerald-900',
    pending: 'bg-slate-100 text-slate-700',
  };
  
  const barColors = {
    sky: 'bg-sky-500',
    indigo: 'bg-indigo-500',
    pink: 'bg-pink-500',
  };
  
  const statusLabels = {
    active: t('status.active'),
    done: t('status.done'),
    pending: t('status.pending'),
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon && <span className="text-sm">{icon}</span>}
          <span className="text-sm font-medium">{label}</span>
          <Badge variant="secondary" className={`text-xs ${statusColors[status]}`}>
            {statusLabels[status]}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {done}/{total}
          </span>
          <span className="text-sm font-medium">{percent}%</span>
        </div>
      </div>
      <div 
        className="h-1.5 bg-slate-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} progress`}
      >
        <div
          className={`h-full ${barColors[color]} transition-all duration-300 ease-out motion-reduce:transition-none`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
