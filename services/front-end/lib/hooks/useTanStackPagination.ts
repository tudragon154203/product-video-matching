'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { usePaginatedList } from './usePaginatedList';
import { shouldEnablePrefetch, paginationConfig } from '@/lib/config/pagination';

interface PaginatedResponse<T> {
    items: T[];
    total: number;
}

interface UseTanStackPaginationOptions<T> {
    queryKey: (offset: number, limit: number) => readonly unknown[];
    fetchFunction: (offset: number, limit: number) => Promise<PaginatedResponse<T>>;
    initialOffset?: number;
    limit?: number;
    enabled?: boolean;
    staleTime?: number;
    gcTime?: number;
    refetchInterval?: number | false;
    disablePrefetch?: boolean; // Option to disable adjacent page prefetching
}

interface UseTanStackPaginationReturn<T> {
    // Data states
    items: T[];
    total: number;
    isLoading: boolean;
    isNavigationLoading: boolean;
    isError: boolean;
    error: Error | null;
    isFetching: boolean;
    isPlaceholderData: boolean;

    // Pagination
    offset: number;
    limit: number;

    // Actions
    handlePrev: () => void;
    handleNext: () => void;
    handleRetry: () => void;

    // TanStack Query specific
    refetch: () => void;
    queryClient: ReturnType<typeof useQueryClient>;
}

export function useTanStackPagination<T>(
    options: UseTanStackPaginationOptions<T>
): UseTanStackPaginationReturn<T> {
    const {
        queryKey: getQueryKey,
        fetchFunction,
        initialOffset = 0,
        limit = 10,
        enabled = true,
        staleTime = paginationConfig.cache.staleTime,
        gcTime = paginationConfig.cache.gcTime,
        refetchInterval = false,
        disablePrefetch = !shouldEnablePrefetch(), // Use centralized config
    } = options;

    const queryClient = useQueryClient();
    const pagination = usePaginatedList(initialOffset, limit);

    // Track navigation loading state separately from query loading
    const [isNavigationLoading, setIsNavigationLoading] = useState(false);

    // Generate query key for current page
    const currentQueryKey = getQueryKey(pagination.offset, limit);

    // Main query for current page
    const {
        data,
        isLoading,
        isError,
        error,
        isFetching,
        isPlaceholderData,
        refetch,
    } = useQuery({
        queryKey: currentQueryKey,
        queryFn: () => fetchFunction(pagination.offset, limit),
        enabled,
        staleTime,
        gcTime,
        refetchInterval,
        placeholderData: keepPreviousData,
        retry: (failureCount, error) => {
            // Reduce retries during active polling to minimize API load
            const maxRetries = refetchInterval
                ? paginationConfig.retry.maxRetriesWhenPolling
                : paginationConfig.retry.maxRetriesDefault;
            return failureCount < maxRetries;
        },
        retryDelay: (attemptIndex) =>
            Math.min(
                paginationConfig.retry.baseRetryDelay * 2 ** attemptIndex,
                paginationConfig.retry.maxRetryDelay
            ),
    });

    // Extract data or provide defaults
    const items = data?.items || [];
    const total = data?.total || 0;

    // Prefetch adjacent pages for better UX (with smart throttling)
    const prefetchAdjacentPages = useCallback(() => {
        const currentOffset = pagination.offset;

        // Skip prefetching during active polling to reduce API load
        if (refetchInterval && isFetching) {
            return;
        }

        // Prefetch previous page
        if (currentOffset > 0) {
            const prevOffset = Math.max(0, currentOffset - limit);
            const prevQueryKey = getQueryKey(prevOffset, limit);

            queryClient.prefetchQuery({
                queryKey: prevQueryKey,
                queryFn: () => fetchFunction(prevOffset, limit),
                staleTime,
                gcTime,
            });
        }

        // Prefetch next page
        if (currentOffset + limit < total) {
            const nextOffset = currentOffset + limit;
            const nextQueryKey = getQueryKey(nextOffset, limit);

            queryClient.prefetchQuery({
                queryKey: nextQueryKey,
                queryFn: () => fetchFunction(nextOffset, limit),
                staleTime,
                gcTime,
            });
        }
    }, [pagination.offset, limit, total, getQueryKey, fetchFunction, queryClient, staleTime, gcTime, refetchInterval, isFetching]);

    // Track when we last prefetched to prevent rapid successive prefetching
    const lastPrefetchRef = useRef<number>(0);

    // Prefetch adjacent pages when data loads successfully (with smart throttling)
    useEffect(() => {
        // Skip prefetching entirely if disabled
        if (disablePrefetch) {
            return;
        }

        if (data && !isPlaceholderData) {
            const now = Date.now();
            // Prevent prefetching if we just did it recently
            const minPrefetchInterval = refetchInterval ? 8000 : 2000; // 8s during polling, 2s otherwise

            if (now - lastPrefetchRef.current > minPrefetchInterval) {
                const delay = refetchInterval ? 3000 : 100; // 3 seconds if actively refetching, 100ms otherwise
                const timer = setTimeout(() => {
                    prefetchAdjacentPages();
                    lastPrefetchRef.current = Date.now();
                }, delay);
                return () => clearTimeout(timer);
            }
        }
    }, [data, isPlaceholderData, prefetchAdjacentPages, refetchInterval, disablePrefetch]);

    // Navigation handlers with loading states
    const handlePrev = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.prev();

        // Reset navigation loading after a short delay
        // TanStack Query will handle the actual loading state
        setTimeout(() => setIsNavigationLoading(false), 100);
    }, [pagination]);

    const handleNext = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.next(total);

        // Reset navigation loading after a short delay
        // TanStack Query will handle the actual loading state
        setTimeout(() => setIsNavigationLoading(false), 100);
    }, [pagination, total]);

    // Retry handler that invalidates current query
    const handleRetry = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: currentQueryKey });
        refetch();
    }, [queryClient, currentQueryKey, refetch]);

    return {
        // Data states
        items,
        total,
        isLoading,
        isNavigationLoading: isNavigationLoading || (isFetching && isPlaceholderData),
        isError,
        error,
        isFetching,
        isPlaceholderData,

        // Pagination
        offset: pagination.offset,
        limit,

        // Actions
        handlePrev,
        handleNext,
        handleRetry,

        // TanStack Query specific
        refetch,
        queryClient,
    };
}