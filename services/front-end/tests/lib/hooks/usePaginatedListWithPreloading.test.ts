import { renderHook, act, waitFor } from '@testing-library/react';
import { usePaginatedListWithPreloading } from '@/lib/hooks/usePaginatedListWithPreloading';

// Mock fetch function for testing
const createMockFetchFunction = (totalItems = 50, delay = 0) => {
    return jest.fn().mockImplementation(async (offset: number, limit: number) => {
        if (delay > 0) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }

        const items = Array.from({ length: Math.min(limit, totalItems - offset) }, (_, i) => ({
            id: offset + i + 1,
            name: `Item ${offset + i + 1}`,
            data: `Data for item ${offset + i + 1}`
        }));

        return {
            items,
            total: totalItems
        };
    });
};

describe('usePaginatedListWithPreloading', () => {
    let mockFetch: jest.Mock;

    beforeEach(() => {
        jest.clearAllMocks();
        mockFetch = createMockFetchFunction();
    });

    test('should initialize with correct default values', () => {
        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch)
        );

        expect(result.current.items).toEqual([]);
        expect(result.current.total).toBe(0);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.isNavigationLoading).toBe(false);
        expect(result.current.isPreloading).toBe(false);
        expect(result.current.error).toBe(null);
        expect(result.current.offset).toBe(0);
        expect(result.current.limit).toBe(10);
    });

    test('should handle successful data loading', async () => {
        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch)
        );

        // Trigger initial load
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(mockFetch).toHaveBeenCalledWith(0, 10);
        expect(result.current.items).toHaveLength(10);
        expect(result.current.total).toBe(50);
        expect(result.current.error).toBe(null);
    });

    test('should handle navigation correctly', async () => {
        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch)
        );

        // Load initial data
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Navigate to next page
        act(() => {
            result.current.handleNext();
        });

        expect(result.current.isNavigationLoading).toBe(true);
        expect(result.current.offset).toBe(10);
    });

    test('should handle previous navigation correctly', async () => {
        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch, { initialOffset: 10 })
        );

        // Load initial data
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Navigate to previous page
        act(() => {
            result.current.handlePrev();
        });

        expect(result.current.isNavigationLoading).toBe(true);
        expect(result.current.offset).toBe(0);
    });

    test('should handle errors gracefully', async () => {
        const errorMessage = 'Network error';
        const errorFetch = jest.fn().mockRejectedValue(new Error(errorMessage));

        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(errorFetch)
        );

        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        await waitFor(() => {
            expect(result.current.error).toBe(errorMessage);
        });

        expect(result.current.items).toEqual([]);
        expect(result.current.total).toBe(0);
    });

    test('should retry correctly after error', async () => {
        const errorFetch = jest.fn()
            .mockRejectedValueOnce(new Error('Network error'))
            .mockImplementation(createMockFetchFunction());

        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(errorFetch)
        );

        // First call should fail
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        await waitFor(() => {
            expect(result.current.error).toBe('Network error');
        });

        // Retry should succeed
        await act(async () => {
            result.current.handleRetry();
        });

        await waitFor(() => {
            expect(result.current.error).toBe(null);
        });

        expect(result.current.items).toHaveLength(10);
    });

    test('should cache and pre-load correctly', async () => {
        const slowFetch = createMockFetchFunction(50, 100); // 100ms delay

        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(slowFetch)
        );

        // Load initial data
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Navigate to next page
        act(() => {
            result.current.handleNext();
        });

        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Go back to first page (should use cache)
        act(() => {
            result.current.handlePrev();
        });

        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Should have made calls for multiple offsets (original + preloading)
        expect(slowFetch).toHaveBeenCalledTimes(3); // 0, 10, and pre-loading
        expect(slowFetch).toHaveBeenCalledWith(0, 10);
        expect(slowFetch).toHaveBeenCalledWith(10, 10);
    });

    test('should clear cache correctly', async () => {
        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch)
        );

        // Load initial data
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        // Clear cache
        act(() => {
            result.current.clearCache();
        });

        // Load data again (should make new API call)
        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    test('should respect custom options', () => {
        const customOptions = {
            initialOffset: 20,
            limit: 5,
            maxCacheSize: 3,
            preloadDelay: 500
        };

        const { result } = renderHook(() =>
            usePaginatedListWithPreloading(mockFetch, customOptions)
        );

        expect(result.current.offset).toBe(20);
        expect(result.current.limit).toBe(5);
    });

    test('should maintain type safety with generic type parameter', async () => {
        interface TestItem {
            id: number;
            name: string;
            data: string;
        }

        const { result } = renderHook(() =>
            usePaginatedListWithPreloading<TestItem>(mockFetch)
        );

        await act(async () => {
            await result.current.loadFromCacheOrFetch();
        });

        await waitFor(() => {
            expect(result.current.items[0]).toHaveProperty('id');
            expect(result.current.items[0]).toHaveProperty('name');
            expect(result.current.items[0]).toHaveProperty('data');
        });
    });
});