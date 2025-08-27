import { useState, useCallback } from 'react';

/**
 * Generic hook for managing paginated list state
 */
export function usePaginatedList(initialOffset = 0, limit = 10) {
  const [offset, setOffset] = useState(initialOffset);

  const next = useCallback((total: number) => {
    setOffset(currentOffset =>
      currentOffset + limit < total ? currentOffset + limit : currentOffset
    );
  }, [limit]);

  const prev = useCallback(() => {
    setOffset(currentOffset => Math.max(0, currentOffset - limit));
  }, [limit]);

  const canPrev = offset > 0;
  const canNext = useCallback((total: number) => offset + limit < total, [offset, limit]);

  const goToPage = useCallback((newOffset: number) => {
    setOffset(Math.max(0, newOffset));
  }, []);

  const reset = useCallback(() => {
    setOffset(initialOffset);
  }, [initialOffset]);

  return {
    offset,
    setOffset,
    limit,
    next,
    prev,
    canPrev,
    canNext,
    goToPage,
    reset,
  };
}