import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useTanStackPagination } from '@/lib/hooks/useTanStackPagination';
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

  // Do not auto-invalidate on every render; rely on query keys changing with jobId
  // to fetch fresh data. This avoids tight refetch loops.

  // Rely solely on React Query's refetchInterval to refresh during collection.
  // Intentionally avoid manual invalidation loops that can cause rapid refetching.
  const prevIsCollecting = useRef(isCollecting);
  useEffect(() => {
    prevIsCollecting.current = isCollecting;
  }, [isCollecting]);

  return pagination;
}
