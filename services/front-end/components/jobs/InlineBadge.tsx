import React from 'react';
import { Badge } from '@/components/ui/badge';

interface InlineBadgeProps {
  text: string;
  variant?: 'default' | 'secondary' | 'outline' | 'destructive';
}

export function InlineBadge({ text, variant = 'default' }: InlineBadgeProps) {
  return <Badge variant={variant}>{text}</Badge>;
}