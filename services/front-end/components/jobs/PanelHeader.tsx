import React from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList';

interface PanelHeaderProps {
  title: string;
  subtitle?: string;
  count?: number;
  children?: React.ReactNode;
}

export function PanelHeader({ title, subtitle, count, children }: PanelHeaderProps) {
  const { parentRef: headerRef } = useAutoAnimateList<HTMLDivElement>()
  return (
    <CardHeader className="pb-4">
      <div className="flex items-center justify-between" ref={headerRef}>
        <div>
          <CardTitle className="text-xl font-semibold">{title}</CardTitle>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {count !== undefined && (
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900 leading-none">{count.toLocaleString()}</span>
              <span className="text-xs text-muted-foreground">total</span>
            </div>
          )}
          {children}
        </div>
      </div>
    </CardHeader>
  );
}
