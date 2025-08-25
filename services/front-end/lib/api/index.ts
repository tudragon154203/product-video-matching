// Export API clients
export { 
  createApiClient, 
  mainApiClient, 
  resultsApiClient, 
  apiRequest 
} from './client';

// Export all services
export * from './services';

// Export utilities
export * from './utils';

// Export phase utilities for backward compatibility
export { 
  getPhaseInfo, 
  getPhasePercent, 
  shouldPoll 
} from './utils/phase';