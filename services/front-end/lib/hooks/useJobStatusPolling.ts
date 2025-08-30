import { useState, useEffect } from 'react';
import { useInterval } from '@mantine/hooks';
import { jobApiService } from '@/lib/api/services/job.api';
import { getPollingInterval } from '@/lib/config/pagination';

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
    images: number;
    frames: number;
  };
}

const POLLING_INTERVAL = getPollingInterval('jobStatus'); // Use centralized config
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
  const [counts, setCounts] = useState<{
    products: number;
    videos: number;
    images: number;
    frames: number;
  }>({ products: 0, videos: 0, images: 0, frames: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCollecting = phase === COLLECTION_PHASE;

  const fetchStatus = async () => {
    // Early return if disabled
    if (!enabled) {
      if (process.env.NODE_ENV === 'development') {
        console.debug(`[useJobStatusPolling] Skipping fetch for job ${jobId} (disabled)`);
      }
      return;
    }

    if (process.env.NODE_ENV === 'development') {
      console.debug(`[useJobStatusPolling] Fetching status for job ${jobId}`);
    }
    try {
      setIsLoading(true);
      setError(null);

      const status = await jobApiService.getJobStatus(jobId);
      setPhase(status.phase);
      setPercent(status.percent);
      setCounts(status.counts); // Use actual counts from API
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
    } else {
      stop(); // Ensure polling is stopped when disabled
    }
  }, [enabled, jobId, start, stop]); // Include all dependencies

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
    counts, // Return actual counts from API
  };
}