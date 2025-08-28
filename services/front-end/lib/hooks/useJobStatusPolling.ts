import { useState, useEffect } from 'react';
import { useInterval } from '@mantine/hooks';
import { jobApiService } from '@/lib/api/services/job.api';

interface UseJobStatusPollingResult {
  phase: string;
  percent: number | undefined;
  isCollecting: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  counts: {
    products: number;
    videos: number;
  };
}

const POLLING_INTERVAL = 5000; // 5 seconds
const COLLECTION_PHASE = 'collection';

export function useJobStatusPolling(
  jobId: string,
  { 
    enabled = true,
    interval = POLLING_INTERVAL 
  } = {}
): UseJobStatusPollingResult {
  const [phase, setPhase] = useState<string>('');
  const [percent, setPercent] = useState<number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const isCollecting = phase === COLLECTION_PHASE;

  const fetchStatus = async () => {
    if (!enabled) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      const status = await jobApiService.getJobStatus(jobId);
      setPhase(status.phase);
      setPercent(status.percent);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job status');
    } finally {
      setIsLoading(false);
    }
  };

  // Use Mantine's useInterval hook for cleaner implementation
  const { start, stop } = useInterval(fetchStatus, interval);

  useEffect(() => {
    if (enabled) {
      fetchStatus(); // Initial fetch
      start();
      return () => stop();
    }
  }, [enabled, jobId]);

  // Stop polling if the job has reached a terminal state (completed or failed)
  useEffect(() => {
    if (phase && (phase === 'completed' || phase === 'failed')) {
      stop();
    }
  }, [phase, stop]);

  return {
    phase,
    percent,
    isCollecting,
    isLoading,
    error,
    refetch: fetchStatus,
    counts: {
      products: 0, // TODO: Implement actual counts from API response
      videos: 0, // TODO: Implement actual counts from API response
    },
  };
}