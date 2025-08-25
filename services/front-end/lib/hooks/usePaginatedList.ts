import { useState } from 'react';

/**
 * Generic hook for managing paginated list state
 */
export function usePaginatedList(initialOffset = 0, limit = 10) {
  const [offset, setOffset] = useState(initialOffset);
  
  const next = (total: number) => {
    setOffset(currentOffset => 
      currentOffset + limit < total ? currentOffset + limit : currentOffset
    );
  };
  
  const prev = () => {
    setOffset(currentOffset => Math.max(0, currentOffset - limit));
  };
  
  const canPrev = offset > 0;
  const canNext = (total: number) => offset + limit < total;
  
  const goToPage = (newOffset: number) => {
    setOffset(Math.max(0, newOffset));
  };
  
  const reset = () => {
    setOffset(initialOffset);
  };
  
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