import { Phase } from '@/lib/zod/job';
import { shouldPoll } from './phase';

/**
 * Configuration for polling behavior
 */
export interface PollingConfig {
  interval: number;
  maxAttempts?: number;
  backoffMultiplier?: number;
  maxInterval?: number;
}

/**
 * Default polling configuration
 */
export const defaultPollingConfig: PollingConfig = {
  interval: 5000, // 5 seconds
  maxAttempts: 720, // 1 hour at 5 second intervals
  backoffMultiplier: 1, // No backoff by default
  maxInterval: 30000, // Max 30 seconds
};

/**
 * Create a polling configuration for different scenarios
 */
export function createPollingConfig(overrides: Partial<PollingConfig> = {}): PollingConfig {
  return { ...defaultPollingConfig, ...overrides };
}

/**
 * Configuration for different polling scenarios
 */
export const pollingConfigs = {
  // Fast polling for recently started jobs
  active: createPollingConfig({
    interval: 2000, // 2 seconds
    maxAttempts: 900, // 30 minutes
  }),
  
  // Normal polling for ongoing jobs
  normal: createPollingConfig({
    interval: 5000, // 5 seconds
    maxAttempts: 720, // 1 hour
  }),
  
  // Slow polling for long-running jobs
  slow: createPollingConfig({
    interval: 10000, // 10 seconds
    maxAttempts: 360, // 1 hour
  }),
  
  // Background polling for completed jobs (health checks)
  background: createPollingConfig({
    interval: 30000, // 30 seconds
    maxAttempts: 120, // 1 hour
  }),
} as const;

/**
 * Determine appropriate polling config based on phase
 */
export function getPollingConfigForPhase(phase: Phase): PollingConfig {
  if (!shouldPoll(phase)) {
    return pollingConfigs.background;
  }
  
  switch (phase) {
    case 'collection':
      return pollingConfigs.active;
    case 'feature_extraction':
      return pollingConfigs.normal;
    case 'matching':
      return pollingConfigs.normal;
    case 'evidence':
      return pollingConfigs.active;
    default:
      return pollingConfigs.normal;
  }
}

/**
 * Calculate next polling interval with exponential backoff
 */
export function calculateNextInterval(
  currentInterval: number,
  config: PollingConfig,
  attemptCount: number
): number {
  if (config.backoffMultiplier === 1) {
    return currentInterval;
  }
  
  const nextInterval = currentInterval * (config.backoffMultiplier || 1.5);
  return Math.min(nextInterval, config.maxInterval || defaultPollingConfig.maxInterval!);
}

/**
 * Check if polling should continue based on attempt count
 */
export function shouldContinuePolling(
  attemptCount: number,
  config: PollingConfig
): boolean {
  if (!config.maxAttempts) {
    return true;
  }
  
  return attemptCount < config.maxAttempts;
}

/**
 * Utility for React Query polling configuration
 */
export function getQueryRefetchInterval(phase: Phase): number | false {
  if (!shouldPoll(phase)) {
    return false;
  }
  
  const config = getPollingConfigForPhase(phase);
  return config.interval;
}