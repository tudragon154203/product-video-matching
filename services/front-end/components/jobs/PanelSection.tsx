import React from 'react';
import { Card } from '@/components/ui/card';

interface PanelSectionProps {
 children: React.ReactNode;
  className?: string;
  'data-testid'?: string;
}

export function PanelSection({ children, className = '', 'data-testid': dataTestId }: PanelSectionProps) {
  return (
    <Card className={`w-full ${className}`} data-testid={dataTestId}>
      <div className="p-4">{children}</div>
    </Card>
  );
}