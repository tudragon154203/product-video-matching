'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePaginatedList } from './usePaginatedList';

interface PaginatedResponse<T> {
    items: T[];
    total: number;
}

interface CacheData<T> {
    items: T[];
    total: number;
}

interface UsePaginatedListWithPreloadingOptions<T> {
    initialOffset?: number;
    limit?: number;
    maxCacheSize?: number;
    preloadDelay?: number;
}

interface UsePaginatedListWithPreloadingReturn<T> {
    // Data states
    items: T[];
    total: number;
    isLoading: boolean;
    isNavigationLoading: boolean;
    isPreloading: boolean;
    error: string | null;

    // Pagination
    offset: number;
    limit: number;

    // Actions
    handlePrev: () => void;
    handleNext: () => void;
    handleRetry: () => void;

    // Cache management
    clearCache: () => void;

    // For external fetch function
    fetchFunction: (showNavigationLoading?: boolean, isAlreadyLoading?: boolean, targetOffset?: number) => Promise<PaginatedResponse<T> | null>;
    loadFromCacheOrFetch: () => Promise<void>;
}

export function usePaginatedListWithPreloading<T>(
    fetchFunction: (offset: number, limit: number) => Promise<PaginatedResponse<T>>,
    options: UsePaginatedListWithPreloadingOptions<T> = {}
): UsePaginatedListWithPreloadingReturn<T> {
    const {
        initialOffset = 0,
        limit = 10,
        maxCacheSize = 5,
        preloadDelay = 100
    } = options;

    // Core states
    const [items, setItems] = useState<T[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [isNavigationLoading, setIsNavigationLoading] = useState(false);
    const [isPreloading, setIsPreloading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Cache state
    const [pageCache, setPageCache] = useState<Map<number, CacheData<T>>>(new Map());

    // Pagination
    const pagination = usePaginatedList(initialOffset, limit);

    // Internal fetch function with caching logic
    const internalFetchFunction = useCallback(async (
        showNavigationLoading = false,
        isAlreadyLoading = false,
        targetOffset?: number
    ): Promise<PaginatedResponse<T> | null> => {
        const fetchOffset = targetOffset ?? pagination.offset;

        try {
            setIsLoading(true);
            if (showNavigationLoading && !isAlreadyLoading) {
                setIsNavigationLoading(true);
            }
            setError(null);

            const response = await fetchFunction(fetchOffset, limit);

            // If this is for the current page, update the main state
            if (fetchOffset === pagination.offset) {
                setItems(response.items);
                setTotal(response.total);
            }

            return response;
        } catch (err) {
            if (fetchOffset === pagination.offset) {
                setError(err instanceof Error ? err.message : 'Failed to load data');
                setItems([]);
                setTotal(0);
            }
            return null;
        } finally {
            setIsLoading(false);
            setIsNavigationLoading(false);
        }
    }, [fetchFunction, limit, pagination.offset]);

    // Pre-load adjacent pages
    const preloadAdjacentPages = useCallback(async (currentOffset: number, totalItems: number) => {
        if (isPreloading) return;

        setIsPreloading(true);
        const pagesToPreload: number[] = [];

        // Previous page
        if (currentOffset > 0) {
            const prevOffset = Math.max(0, currentOffset - limit);
            if (!pageCache.has(prevOffset)) {
                pagesToPreload.push(prevOffset);
            }
        }

        // Next page
        if (currentOffset + limit < totalItems) {
            const nextOffset = currentOffset + limit;
            if (!pageCache.has(nextOffset)) {
                pagesToPreload.push(nextOffset);
            }
        }

        // Load pages in parallel
        const preloadPromises = pagesToPreload.map(async (offset) => {
            try {
                const response = await internalFetchFunction(false, false, offset);
                if (response) {
                    setPageCache(prev => {
                        const newCache = new Map(prev);
                        newCache.set(offset, { items: response.items, total: response.total });

                        // Limit cache size to prevent memory issues
                        if (newCache.size > maxCacheSize) {
                            const oldestKey = Array.from(newCache.keys())[0];
                            newCache.delete(oldestKey);
                        }

                        return newCache;
                    });
                }
            } catch (error) {
                // Silent fail for pre-loading
                console.warn('Pre-loading failed for offset:', offset, error);
            }
        });

        await Promise.all(preloadPromises);
        setIsPreloading(false);
    }, [isPreloading, limit, pageCache, internalFetchFunction, maxCacheSize]);

    // Check if we have cached data for current page
    const loadFromCacheOrFetch = useCallback(async () => {
        const cachedData = pageCache.get(pagination.offset);

        if (cachedData) {
            // Use cached data immediately
            setItems(cachedData.items);
            setTotal(cachedData.total);
            setError(null);

            // Pre-load adjacent pages in background
            setTimeout(() => preloadAdjacentPages(pagination.offset, cachedData.total), preloadDelay);
        } else {
            // Fetch current page
            const response = await internalFetchFunction(true, true);
            if (response) {
                // Cache current page
                setPageCache(prev => {
                    const newCache = new Map(prev);
                    newCache.set(pagination.offset, { items: response.items, total: response.total });
                    return newCache;
                });

                // Pre-load adjacent pages in background
                setTimeout(() => preloadAdjacentPages(pagination.offset, response.total), preloadDelay);
            }
        }
    }, [pageCache, pagination.offset, preloadAdjacentPages, internalFetchFunction, preloadDelay]);

    // Navigation handlers
    const handlePrev = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.prev();
    }, [pagination]);

    const handleNext = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.next(total);
    }, [pagination, total]);

    const handleRetry = useCallback(() => {
        setPageCache(new Map());
        internalFetchFunction(true);
    }, [internalFetchFunction]);

    // Cache management
    const clearCache = useCallback(() => {
        setPageCache(new Map());
    }, []);

    return {
        // Data states
        items,
        total,
        isLoading,
        isNavigationLoading,
        isPreloading,
        error,

        // Pagination
        offset: pagination.offset,
        limit,

        // Actions
        handlePrev,
        handleNext,
        handleRetry,

        // Cache management
        clearCache,

        // Functions for external use
        fetchFunction: internalFetchFunction,
        loadFromCacheOrFetch,
    };
}