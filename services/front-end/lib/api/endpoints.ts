/**
 * API endpoints configuration for main-api service
 */
export const MAIN_API_ENDPOINTS = {
  // Job endpoints
  jobs: {
    start: '/start-job',
    status: (jobId: string) => `/status/${jobId}`,
    list: '/jobs',
  },
  
  // Product endpoints
  products: {
    byJob: (jobId: string) => `/jobs/${jobId}/products`,
  },
  
  // Video endpoints
  videos: {
    byJob: (jobId: string) => `/jobs/${jobId}/videos`,
    frames: (jobId: string, videoId: string) => `/jobs/${jobId}/videos/${videoId}/frames`,
  },
  
  // Image endpoints
  images: {
    byJob: (jobId: string) => `/jobs/${jobId}/images`,
  },
  
  // Feature endpoints
  features: {
    summary: (jobId: string) => `/jobs/${jobId}/features/summary`,
    productImages: (jobId: string) => `/jobs/${jobId}/features/product-images`,
    videoFrames: (jobId: string) => `/jobs/${jobId}/features/video-frames`,
    productImage: (imgId: string) => `/features/product-images/${imgId}`,
    videoFrame: (frameId: string) => `/features/video-frames/${frameId}`,
  },
  
  // Health endpoint
  health: '/health',
} as const;

/**
 * API endpoints configuration for results-api service
 */
export const RESULTS_API_ENDPOINTS = {
  // Match endpoints
  matches: {
    byJob: (jobId: string) => `/jobs/${jobId}/matches`,
    detail: (matchId: string) => `/matches/${matchId}`,
    evidence: (matchId: string) => `/matches/${matchId}/evidence`,
  },
  
  // Statistics endpoint
  stats: '/stats',
  
  // Health endpoint
  health: '/health',
} as const;

/**
 * All API endpoints combined
 */
export const API_ENDPOINTS = {
  main: MAIN_API_ENDPOINTS,
  results: RESULTS_API_ENDPOINTS,
} as const;