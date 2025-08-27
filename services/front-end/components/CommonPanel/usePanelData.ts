import { useCallback, useEffect } from 'react';
import { useTanStackPagination } from '@/lib/hooks/useTanStackPagination';
import { queryKeys } from '@/lib/api/hooks';

interface UsePanelDataProps<T> {
  jobId: string;
  isCollecting?: boolean;
  limit?: number;
  fetchFunction: (offset: number, limit: number) => Promise<{ items: T[]; total: number }>;
  queryKey: (offset: number, limit: number) => unknown[];
  enabled?: boolean;
}

export function usePanelData<T>({
  jobId,
  isCollecting = false,
  limit = 10,
  fetchFunction,
  queryKey,
  enabled = true,
}: UsePanelDataProps<T>) {
  const fetchPanelData = useCallback(async (offset: number, limit: number) => {
    if (!jobId) throw new Error('Job ID is required');
    return await fetchFunction(offset, limit);
 }, [jobId, fetchFunction]);

 const pagination = useTanStackPagination<T>({
    queryKey: (offset, limit) => queryKey(offset, limit),
    fetchFunction: fetchPanelData,
    limit,
    enabled: !!jobId && enabled && !isCollecting,
    refetchInterval: isCollecting ? 5000 : false,
    staleTime: isCollecting ? 0 : 1000 * 60 * 5, // 5 minutes when not collecting, immediate when collecting
  });

  // Clear cache when job changes
  useEffect(() => {
    if (pagination.queryClient && typeof pagination.queryClient.invalidateQueries === 'function') {
      pagination.queryClient.invalidateQueries({ queryKey: queryKey(0, limit) });
    }
  }, [jobId, pagination.queryClient, queryKey, limit]);

 return pagination;
}