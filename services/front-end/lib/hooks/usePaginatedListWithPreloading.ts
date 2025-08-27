'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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
    pollCurrentPage: () => Promise<void>;
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

    // Cache state - using useRef for synchronous access
    const pageCacheRef = useRef<Map<number, CacheData<T>>>(new Map());

    // Cache management constants
    const MAX_CACHE_SIZE = maxCacheSize;

    // Pagination
    const pagination = usePaginatedList(initialOffset, limit);

    // Helper function to compare arrays for equality
    const arraysEqual = useCallback((a: T[], b: T[]) => {
        if (a.length !== b.length) return false;
        return JSON.stringify(a) === JSON.stringify(b);
    }, []);

    // Cache page data synchronously - only if data has changed
    const cachePageData = useCallback((offset: number, items: T[], total: number, forceUpdate = false) => {
        const currentCache = pageCacheRef.current;
        const existing = currentCache.get(offset);

        // Check if data has actually changed
        const hasChanged = !existing ||
            existing.total !== total ||
            !arraysEqual(existing.items, items);

        if (!hasChanged && !forceUpdate) {
            console.log(`⏭️ [CACHE] Data unchanged for offset ${offset}, skipping cache update`);
            return false;
        }

        console.log(`💾 [CACHE] Caching ${hasChanged ? 'changed' : 'forced'} data for offset ${offset}`);
        console.log(`📊 [CACHE] Data: ${items.length} items, total: ${total}`);
        console.log(`🗂️ [CACHE] Before: cache size ${currentCache.size}, keys: [${Array.from(currentCache.keys()).join(', ')}]`);

        currentCache.set(offset, { items, total });

        console.log(`✅ [CACHE] Successfully cached offset ${offset}`);
        console.log(`🗂️ [CACHE] After: cache size ${currentCache.size}, keys: [${Array.from(currentCache.keys()).join(', ')}]`);

        // Keep cache size reasonable
        if (currentCache.size > MAX_CACHE_SIZE) {
            const oldestKey = currentCache.keys().next().value;
            if (oldestKey !== undefined) {
                console.log(`🗑️ [CACHE] Cache size exceeded ${MAX_CACHE_SIZE}, removing oldest: ${oldestKey}`);
                currentCache.delete(oldestKey);
                console.log(`🗂️ [CACHE] After cleanup: cache size ${currentCache.size}, keys: [${Array.from(currentCache.keys()).join(', ')}]`);
            }
        }

        return true;
    }, [arraysEqual]);

    // Internal fetch function with intelligent caching
    const internalFetchFunction = useCallback(async (
        showNavigationLoading = false,
        isAlreadyLoading = false,
        targetOffset?: number
    ): Promise<PaginatedResponse<T> | null> => {
        const fetchOffset = targetOffset ?? pagination.offset;

        console.log(`🔄 [FETCH] Starting fetch for offset ${fetchOffset}`);

        try {
            setIsLoading(true);
            if (showNavigationLoading && !isAlreadyLoading) {
                setIsNavigationLoading(true);
            }
            setError(null);

            const response = await fetchFunction(fetchOffset, limit);

            console.log(`✅ [FETCH] API response for offset ${fetchOffset}: ${response.items.length} items, total: ${response.total}`);

            // Cache the response and check if data actually changed
            const dataChanged = cachePageData(fetchOffset, response.items, response.total);

            // If this is for the current page, update the main state only if data changed
            if (fetchOffset === pagination.offset) {
                if (dataChanged || items.length === 0) {
                    console.log(`🔄 [STATE] Updating main state for offset ${fetchOffset} (dataChanged: ${dataChanged})`);
                    setItems(response.items);
                    setTotal(response.total);
                } else {
                    console.log(`⏭️ [STATE] Skipping state update for offset ${fetchOffset} - no changes detected`);
                }
            }

            return response;
        } catch (err) {
            console.error(`❌ [FETCH] Error fetching offset ${fetchOffset}:`, err);
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
    }, [fetchFunction, limit, pagination.offset, cachePageData, items.length]);

    // Pre-load adjacent pages with synchronous caching
    const preloadAdjacentPages = useCallback(async (currentOffset: number, totalItems: number) => {
        if (isPreloading) return;

        setIsPreloading(true);

        console.log(`🔄 [PRELOAD] Starting pre-load for offset ${currentOffset}`);

        const currentCache = pageCacheRef.current;
        const pagesToPreload: number[] = [];

        // Previous page
        if (currentOffset > 0) {
            const prevOffset = Math.max(0, currentOffset - limit);
            if (!currentCache.has(prevOffset)) {
                pagesToPreload.push(prevOffset);
            } else {
                console.log(`⏭️ [PRELOAD] Previous page ${prevOffset} already cached`);
            }
        }

        // Next page
        if (currentOffset + limit < totalItems) {
            const nextOffset = currentOffset + limit;
            if (!currentCache.has(nextOffset)) {
                pagesToPreload.push(nextOffset);
            } else {
                console.log(`⏭️ [PRELOAD] Next page ${nextOffset} already cached`);
            }
        }

        console.log(`📋 [PRELOAD] Pages to pre-load: [${pagesToPreload.join(', ')}]`);

        // Load pages in parallel
        if (pagesToPreload.length > 0) {
            Promise.all(pagesToPreload.map(async (offset) => {
                try {
                    console.log(`⬇️ [PRELOAD] Loading offset ${offset}`);
                    const response = await internalFetchFunction(false, false, offset);
                    if (response) {
                        console.log(`✅ [PRELOAD] Successfully loaded and cached offset ${offset}`);
                    }
                } catch (error) {
                    console.warn(`⚠️ [PRELOAD] Failed to load offset ${offset}:`, error);
                }
            })).finally(() => {
                console.log(`🏁 [PRELOAD] Pre-loading completed for offset ${currentOffset}`);
                setIsPreloading(false);
            });
        } else {
            console.log(`🔄 [PRELOAD] No pages to pre-load for offset ${currentOffset}`);
            setIsPreloading(false);
        }
    }, [isPreloading, limit, internalFetchFunction]);

    // Check if we have cached data for current page and load synchronously
    const loadFromCacheOrFetch = useCallback(async () => {
        const currentOffset = pagination.offset;
        const currentCache = pageCacheRef.current;

        console.log(`🔍 [LOAD] Loading data for offset ${currentOffset}`);
        console.log(`📊 [LOAD] Cache state:`, {
            size: currentCache.size,
            keys: Array.from(currentCache.keys()),
            hasCurrentOffset: currentCache.has(currentOffset)
        });

        const cachedData = currentCache.get(currentOffset);

        if (cachedData) {
            // Use cached data immediately - NO API CALL!
            console.log(`✅ [CACHE HIT] Using cached data for offset ${currentOffset} - INSTANT RESPONSE!`);
            console.log(`📦 [CACHE HIT] Data: ${cachedData.items.length} items, total: ${cachedData.total}`);

            setItems(cachedData.items);
            setTotal(cachedData.total);
            setError(null);
            setIsLoading(false);
            setIsNavigationLoading(false);

            // Pre-load adjacent pages in background
            setTimeout(() => {
                preloadAdjacentPages(currentOffset, cachedData.total);
            }, preloadDelay);
        } else {
            // Fetch current page
            console.log(`❌ [CACHE MISS] No cached data for offset ${currentOffset}, making API call...`);
            const response = await internalFetchFunction(true, true);
            if (response) {
                console.log(`✅ [API SUCCESS] Data fetched and cached, scheduling pre-load...`);
                // Pre-load adjacent pages in background
                setTimeout(() => {
                    preloadAdjacentPages(currentOffset, response.total);
                }, preloadDelay);
            }
        }
    }, [pagination.offset, preloadAdjacentPages, internalFetchFunction, preloadDelay]);

    // Poll current page for updates without showing loading indicators
    const pollCurrentPage = useCallback(async () => {
        const currentOffset = pagination.offset;
        console.log(`🔄 [POLL] Polling for updates at offset ${currentOffset}`);

        // Use internal fetch without navigation loading indicators
        await internalFetchFunction(false, false, currentOffset);
    }, [pagination.offset, internalFetchFunction]);

    // Navigation handlers
    const handlePrev = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.prev();
    }, [pagination]);

    const handleNext = useCallback(() => {
        setIsNavigationLoading(true);
        pagination.next(total);
    }, [pagination, total]);

    // Cache management
    const clearCache = useCallback(() => {
        const newCache = new Map<number, CacheData<T>>();
        pageCacheRef.current = newCache;
        console.log('🗑️ [CACHE] Cache cleared completely');
    }, []);

    const handleRetry = useCallback(() => {
        clearCache();
        internalFetchFunction(true);
    }, [internalFetchFunction, clearCache]);

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
        pollCurrentPage,
    };
}