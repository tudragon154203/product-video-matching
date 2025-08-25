import React from 'react';
import { Separator } from '@/components/ui/separator';

interface ListDividerProps {
  className?: string;
}

export function ListDivider({ className = '' }: ListDividerProps) {
  return <Separator className={className} />;
}