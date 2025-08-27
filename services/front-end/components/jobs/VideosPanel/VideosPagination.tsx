import React from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

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
  const t = useTranslations('jobResults.pagination');
  const canPrev = offset > 0;
  const canNext = offset + limit < total;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const startItem = offset + 1;
  const endItem = Math.min(offset + limit, total);

  if (total <= limit) return null;

  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t">
      <Button
        variant="outline"
        size="sm"
        onClick={onPrev}
        disabled={!canPrev || isLoading}
        className="flex items-center gap-1"
        data-testid="videos-pagination-prev"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
        {t('previous')}
      </Button>

      <div className="text-sm text-muted-foreground flex items-center gap-2" data-testid="videos-pagination-current">
        {isLoading && (
          <Loader2 className="h-4 w-4 animate-spin" />
        )}
        {t('pageInfo', {
          currentPage,
          totalPages,
          start: startItem,
          end: endItem,
          totalItems: total
        })}
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={!canNext || isLoading}
        className="flex items-center gap-1"
        data-testid="videos-pagination-next"
      >
        {t('next')}
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}