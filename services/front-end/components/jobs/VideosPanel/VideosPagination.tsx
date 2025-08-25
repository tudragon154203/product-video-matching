import React from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface VideosPaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPrev: () => void;
  onNext: () => void;
  isLoading?: boolean;
}

export function VideosPagination({
  total,
  limit,
  offset,
  onPrev,
  onNext,
  isLoading = false,
}: VideosPaginationProps) {
  const canPrev = offset > 0;
  const canNext = offset + limit < total;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (total <= limit) return null;

  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t">
      <Button
        variant="outline"
        size="sm"
        onClick={onPrev}
        disabled={!canPrev || isLoading}
        className="flex items-center gap-1"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </Button>
      
      <div className="text-sm text-muted-foreground">
        Page {currentPage} of {totalPages} ({(offset + 1)}-{Math.min(offset + limit, total)} of {total})
      </div>
      
      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={!canNext || isLoading}
        className="flex items-center gap-1"
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}