import React from 'react';
import { Card } from '@/components/ui/card';

interface PanelSectionProps {
  children: React.ReactNode;
  className?: string;
}

export function PanelSection({ children, className = '' }: PanelSectionProps) {
  return (
    <Card className={`w-full ${className}`}>
      <div className="p-4">{children}</div>
    </Card>
  );
}