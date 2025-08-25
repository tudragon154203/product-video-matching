import { Phase } from '@/lib/zod/job';

/**
 * Phase information with UI display properties
 */
export interface PhaseInfo {
  label: string;
  color: string;
  description?: string;
}

/**
 * Phase information mapping for UI display
 */
export const phaseInfo: Record<Phase, PhaseInfo> = {
  unknown: { 
    label: 'Unknown', 
    color: 'gray',
    description: 'Job status is unknown or not initialized'
  },
  collection: { 
    label: 'Collection', 
    color: 'blue',
    description: 'Collecting products and videos'
  },
  feature_extraction: { 
    label: 'Feature Extraction', 
    color: 'yellow',
    description: 'Extracting features from images and video frames'
  },
  matching: { 
    label: 'Matching', 
    color: 'purple',
    description: 'Finding matches between products and videos'
  },
  evidence: { 
    label: 'Evidence Building', 
    color: 'orange',
    description: 'Generating visual evidence for matches'
  },
  completed: { 
    label: 'Completed', 
    color: 'green',
    description: 'Job completed successfully'
  },
  failed: { 
    label: 'Failed', 
    color: 'red',
    description: 'Job failed during processing'
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