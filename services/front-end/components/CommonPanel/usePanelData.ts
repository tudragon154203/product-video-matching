import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useTanStackPagination } from '@/lib/hooks/useTanStackPagination';
import { queryKeys } from '@/lib/api/hooks';
import { shouldEnablePrefetch, getPollingInterval } from '@/lib/config/pagination';

interface UsePanelDataProps<T> {
  jobId: string;
  isCollecting?: boolean;
  limit?: number;
  fetchFunction: (offset: number, limit: number) => Promise<{ items: T[]; total: number }>;
  queryKey: (offset: number, limit: number) => unknown[];
  enabled?: boolean;
  disablePrefetch?: boolean; // Option to disable prefetching to reduce API load
}

export function usePanelData<T>({
  jobId,
  isCollecting = false,
  limit = 10,
  fetchFunction,
  queryKey,
  enabled = true,
  disablePrefetch = !shouldEnablePrefetch(), // Use centralized config
}: UsePanelDataProps<T>) {
  const fetchPanelData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');
    return await fetchFunction(offset, limit);
  }, [jobId, fetchFunction]);

  // Memoize pagination options to ensure TanStack Query reacts to isCollecting changes
  const paginationOptions = useMemo(() => ({
    queryKey: (offset: number, limit: number) => queryKey(offset, limit),
    fetchFunction: fetchPanelData,
    limit,
    enabled: !!jobId && enabled,
    refetchInterval: (isCollecting ? getPollingInterval('panelData') : false) as number | false,
    staleTime: isCollecting ? 0 : 1000 * 60 * 5, // 5 minutes when not collecting, immediate when collecting
    disablePrefetch, // Pass through prefetch disable option
  }), [queryKey, fetchPanelData, limit, jobId, enabled, isCollecting, disablePrefetch]);

  const pagination = useTanStackPagination<T>(paginationOptions);

  // Clear cache when job changes (only invalidate current page, not all pages)
  useEffect(() => {
    if (pagination.queryClient && typeof pagination.queryClient.invalidateQueries === 'function') {
      // Only invalidate the first page to avoid excessive cache clearing
      pagination.queryClient.invalidateQueries({ queryKey: queryKey(0, limit) });
    }
  }, [jobId, pagination.queryClient, queryKey, limit]);

  // Invalidate queries when isCollecting changes to ensure fresh data (debounced)
  useEffect(() => {
    if (pagination.queryClient && typeof pagination.queryClient.invalidateQueries === 'function' && isCollecting) {
      // Only invalidate when starting collection, not on every change
      // Add a small delay to avoid rapid invalidations
      const timer = setTimeout(() => {
        pagination.queryClient.invalidateQueries({
          predicate: (query) => {
            const key = query.queryKey;
            return Array.isArray(key) && key.some(k =>
              typeof k === 'string' && (k.includes('products') || k.includes('videos')) &&
              key.some(v => v === jobId)
            );
          }
        });
      }, 1000); // 1 second delay to debounce rapid changes

      return () => clearTimeout(timer);
    }
  }, [isCollecting, jobId, pagination.queryClient]);

  // Final refresh when transitioning out of collection phase to capture any missed data
  const prevIsCollecting = useRef(isCollecting);
  useEffect(() => {
    if (pagination.queryClient && typeof pagination.queryClient.invalidateQueries === 'function') {
      // If we were collecting and now we're not, do a final refresh to capture any missed data
      if (prevIsCollecting.current === true && isCollecting === false) {
        console.log('Collection phase ended - performing final refresh to capture any missed data');
        // More targeted invalidation - only current view, not all cached pages
        const currentQueryKey = queryKey(pagination.offset || 0, limit);
        pagination.queryClient.invalidateQueries({ queryKey: currentQueryKey });

        // Also invalidate the first page to ensure fresh data
        if (pagination.offset !== 0) {
          pagination.queryClient.invalidateQueries({ queryKey: queryKey(0, limit) });
        }
      }
    }
    prevIsCollecting.current = isCollecting;
  }, [isCollecting, jobId, pagination.queryClient, pagination.offset, queryKey, limit]);

  return pagination;
}