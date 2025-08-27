import React from 'react';
import { cn } from '@/lib/utils';

interface ProductsSkeletonProps {
 count: number;
  'data-testid'?: string;
}

export function ProductsSkeleton({ count, 'data-testid': dataTestId }: ProductsSkeletonProps) {
  return (
    <div className="space-y-3" data-testid={dataTestId}>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "flex items-center gap-3 p-2 rounded-md",
            "border border-muted bg-muted/50"
          )}
        >
          <div className="flex-shrink-0">
            <div className="w-16 h-16 bg-muted rounded-md animate-pulse" />
          </div>
          
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-muted rounded animate-pulse" />
            <div className="h-3 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
          </div>
          
          <div className="w-5 h-5 bg-muted rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}