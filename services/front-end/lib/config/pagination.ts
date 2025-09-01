/**
 * Pagination configuration
 * Use this file to control pagination behavior across the application
 * 
 * Note: Individual job status polling has been permanently disabled to eliminate
 * N+1 API call patterns. Job sidebar now uses phase data from the main /jobs list.
 */

export const paginationConfig = {
    /**
     * PREFETCH CONTROL
     * Set to true to enable adjacent page prefetching
     * Set to false to disable prefetching (reduces API calls)
     * 
     * TEMPORARY: Currently set to false to test API load reduction
     * Change back to true once API request frequency issue is resolved
     */
    enablePrefetch: true,

    /**
     * POLLING INTERVALS (in milliseconds)
     * Adjust these values to control how frequently the UI polls for updates
     */
    polling: {
        // Panel data polling during collection phase
        panelDataInterval: 5000,

        // Job status polling
        jobStatusInterval: 10000,

        // Job sidebar polling
        jobSidebarInterval: 10000,
    },

    /**
     * CACHE CONFIGURATION
     * Controls how long data stays fresh before refetching
     */
    cache: {
        // How long data is considered fresh (stale time)
        staleTime: 1000 * 60 * 5, // 5 minutes default

        // How long data stays in cache before garbage collection
        gcTime: 1000 * 60 * 10, // 10 minutes default
    },

    /**
     * RETRY CONFIGURATION
     * Controls how requests are retried on failure
     */
    retry: {
        // Maximum retries during active polling (reduced to minimize API load)
        maxRetriesWhenPolling: 1,

        // Maximum retries when not polling
        maxRetriesDefault: 3,

        // Base delay between retries (milliseconds)
        baseRetryDelay: 2000,

        // Maximum retry delay (milliseconds)
        maxRetryDelay: 30000,
    }
};

/**
 * Helper function to determine if prefetching should be enabled
 * Can be used to conditionally enable prefetching based on environment or feature flags
 */
export function shouldEnablePrefetch(): boolean {
    // In development, you might want to enable prefetching for testing
    if (process.env.NODE_ENV === 'development' && process.env.ENABLE_PREFETCH === 'true') {
        return true;
    }

    return paginationConfig.enablePrefetch;
}

/**
 * Get polling interval for a specific component
 */
export function getPollingInterval(component: 'panelData' | 'jobStatus' | 'jobSidebar'): number {
    return paginationConfig.polling[`${component}Interval`];
}