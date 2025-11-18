import { type Phase } from '@/lib/zod/job';

/**
 * Phase information with UI display properties
 */
export interface PhaseInfo {
  getLabel: (t?: any) => string;
  getCompactLabel?: (t?: any) => string;
  color: string;
  getDescription?: (t?: any) => string;
  effect?: 'spinner' | 'progress-bar' | 'animated-dots' | 'none';
}

/**
 * Phase information mapping for UI display
 */
export const phaseInfo: Record<Phase, PhaseInfo> = {
  unknown: {
    getLabel: (t) => t('jobStatus.unknown') || 'Status unknown.',
    color: 'bg-gray-500',
    getDescription: (t) => t('jobStatus.unknownDescription') || 'Job status is unknown or not initialized.',
    effect: 'none'
  },
  collection: {
    getLabel: (t) => t('jobStatus.collection') || '',
    getCompactLabel: (t) => t('jobStatus.collectionCompact') || 'Collecting',
    color: 'bg-blue-500',
    getDescription: (t) => t('jobStatus.collectionDescription') || 'Collecting candidate products and videos.',
    effect: 'progress-bar'
  },
  feature_extraction: {
    getLabel: (t) => t('phases.featureExtraction.label') || 'Extracting features (images / video frames)…',
    getCompactLabel: (t) => t('phases.featureExtraction.compact') || 'Extracting',
    color: 'bg-yellow-500',
    getDescription: (t) => t('phases.featureExtraction.description') || 'Extracting visual features from product images and video frames.',
    effect: 'progress-bar'
  },
  matching: {
    getLabel: (t) => t('phases.matching.label') || 'Matching products with videos…',
    getCompactLabel: (t) => t('phases.matching.compact') || 'Matching',
    color: 'bg-purple-500',
    getDescription: (t) => t('phases.matching.description') || 'Matching collected products with candidate videos.',
    effect: 'progress-bar'
  },
  evidence: {
    getLabel: (t) => t('phases.evidence.label') || 'Generating visual evidence…',
    getCompactLabel: (t) => t('phases.evidence.compact') || 'Evidence',
    color: 'bg-orange-500',
    getDescription: (t) => t('phases.evidence.description') || 'Building visual evidence packets for matched products and videos.',
    effect: 'progress-bar'
  },
  completed: {
    getLabel: (t) => t('jobStatus.completed') || '✅ Completed!',
    color: 'bg-green-500',
    getDescription: (t) => t('jobStatus.completedDescription') || 'Job completed successfully.',
    effect: 'none'
  },
  failed: {
    getLabel: (t) => t('jobStatus.failed') || '❌ Job failed.',
    color: 'bg-red-500',
    getDescription: (t) => t('jobStatus.failedDescription') || 'Job failed during processing.',
    effect: 'none'
  },
  cancelled: {
    getLabel: (t) => t('jobStatus.cancelled') || 'Cancelled',
    color: 'bg-gray-500',
    getDescription: (t) => t('jobStatus.cancelledDescription') || 'Job was cancelled by user.',
    effect: 'none'
  },
} as const;

const FALLBACK_PHASE: Phase = 'unknown';

/**
 * Get phase information for UI display
 */
export function getPhaseInfo(phase: Phase | string): PhaseInfo {
  if (typeof phase === 'string' && phase in phaseInfo) {
    return phaseInfo[phase as Phase];
  }

  return phaseInfo[FALLBACK_PHASE];
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
    cancelled: 0,
  };
  return phaseToPercent[phase] || 0;
}

/**
 * Check if a job phase should continue polling
 */
export function shouldPoll(phase: Phase): boolean {
  return phase !== 'completed' && phase !== 'failed' && phase !== 'cancelled';
}

/**
 * Check if a phase is in progress (not terminal)
 */
export function isPhaseInProgress(phase: Phase): boolean {
  return phase !== 'completed' && phase !== 'failed' && phase !== 'cancelled' && phase !== 'unknown';
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
