import { Phase } from '@/lib/zod/job';

/**
 * Phase information with UI display properties
 */
export interface PhaseInfo {
  label: string;
  color: string;
  description?: string;
  effect?: 'spinner' | 'progress-bar' | 'animated-dots' | 'none';
}

/**
 * Phase information mapping for UI display
 */
export const phaseInfo: Record<Phase, PhaseInfo> = {
  unknown: {
    label: 'Status unknown.',
    color: 'gray',
    description: 'Job status is unknown or not initialized',
    effect: 'none'
  },
  collection: {
    label: 'Collecting products and videos…',
    color: 'blue',
    description: 'Collecting products and videos',
    effect: 'animated-dots'
  },
  feature_extraction: {
    label: 'Extracting features (images / video frames)…',
    color: 'yellow',
    description: 'Extracting features from images and video frames',
    effect: 'progress-bar'
  },
  matching: {
    label: 'Matching products with videos…',
    color: 'purple',
    description: 'Finding matches between products and videos',
    effect: 'spinner'
  },
  evidence: {
    label: 'Generating visual evidence…',
    color: 'orange',
    description: 'Generating visual evidence for matches',
    effect: 'progress-bar'
  },
  completed: {
    label: '✅ Completed!',
    color: 'green',
    description: 'Job completed successfully',
    effect: 'none'
  },
  failed: {
    label: '❌ Job failed.',
    color: 'red',
    description: 'Job failed during processing',
    effect: 'none'
  },
} as const;

/**
 * Get phase information for UI display
 */
export function getPhaseInfo(phase: Phase): PhaseInfo {
  return phaseInfo[phase];
}

/**
 * Calculate completion percentage based on phase
 */
export function getPhasePercent(phase: Phase): number {
  const phaseToPercent: Record<Phase, number> = {
    unknown: 0,
    collection: 20,
    feature_extraction: 50,
    matching: 80,
    evidence: 90,
    completed: 100,
    failed: 0,
  };
  return phaseToPercent[phase] || 0;
}

/**
 * Check if a job phase should continue polling
 */
export function shouldPoll(phase: Phase): boolean {
  return phase !== 'completed' && phase !== 'failed';
}

/**
 * Check if a phase is in progress (not terminal)
 */
export function isPhaseInProgress(phase: Phase): boolean {
  return phase !== 'completed' && phase !== 'failed' && phase !== 'unknown';
}

/**
 * Check if a phase represents a successful completion
 */
export function isPhaseCompleted(phase: Phase): boolean {
  return phase === 'completed';
}

/**
 * Check if a phase represents a failure
 */
export function isPhaseFailed(phase: Phase): boolean {
  return phase === 'failed';
}

/**
 * Get all phases in processing order
 */
export function getPhaseOrder(): Phase[] {
  return ['collection', 'feature_extraction', 'matching', 'evidence', 'completed'];
}

/**
 * Get the next expected phase
 */
export function getNextPhase(currentPhase: Phase): Phase | null {
  const order = getPhaseOrder();
  const currentIndex = order.indexOf(currentPhase);
  
  if (currentIndex === -1 || currentIndex === order.length - 1) {
    return null;
  }
  
  return order[currentIndex + 1];
}