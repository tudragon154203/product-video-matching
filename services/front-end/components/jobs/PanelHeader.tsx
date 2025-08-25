import React from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface PanelHeaderProps {
  title: string;
  subtitle?: string;
  count?: number;
  children?: React.ReactNode;
}

export function PanelHeader({ title, subtitle, count, children }: PanelHeaderProps) {
  return (
    <CardHeader className="pb-4">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="text-xl font-semibold">{title}</CardTitle>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        {count !== undefined && (
          <Badge variant="secondary">{count.toLocaleString()}</Badge>
        )}
        {children}
      </div>
    </CardHeader>
  );
}