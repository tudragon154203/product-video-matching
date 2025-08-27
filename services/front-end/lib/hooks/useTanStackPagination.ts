'use client';

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { usePaginatedList } from './usePaginatedList';

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
        staleTime = 1000 * 60 * 5, // 5 minutes default
        gcTime = 1000 * 60 * 10, // 10 minutes default
        refetchInterval = false,
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
        retry: 3,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    });

    // Extract data or provide defaults
    const items = data?.items || [];
    const total = data?.total || 0;

    // Prefetch adjacent pages for better UX
    const prefetchAdjacentPages = useCallback(() => {
        const currentOffset = pagination.offset;

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
    }, [pagination.offset, limit, total, getQueryKey, fetchFunction, queryClient, staleTime, gcTime]);

    // Prefetch adjacent pages when data loads successfully
    useEffect(() => {
        if (data && !isPlaceholderData) {
            // Small delay to avoid blocking the main thread
            const timer = setTimeout(prefetchAdjacentPages, 100);
            return () => clearTimeout(timer);
        }
    }, [data, isPlaceholderData, prefetchAdjacentPages]);

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