import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCancelJob, useDeleteJob } from '../hooks';
import { jobApiService } from '../services/job.api';

// Mock the job API service
jest.mock('../services/job.api');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('Job Action Hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useCancelJob', () => {
    it('should cancel a job successfully', async () => {
      const mockResponse = {
        job_id: 'test-job-id',
        phase: 'cancelled',
        cancelled_at: '2025-11-18T10:30:00Z',
        reason: 'user_request',
      };

      (jobApiService.cancelJob as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useCancelJob(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        jobId: 'test-job-id',
        request: { reason: 'user_request' },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(jobApiService.cancelJob).toHaveBeenCalledWith('test-job-id', {
        reason: 'user_request',
      });
      expect(result.current.data).toEqual(mockResponse);
    });

    it('should handle cancel job error', async () => {
      const mockError = new Error('Failed to cancel job');
      (jobApiService.cancelJob as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useCancelJob(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        jobId: 'test-job-id',
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toEqual(mockError);
    });
  });

  describe('useDeleteJob', () => {
    it('should delete a job successfully', async () => {
      const mockResponse = {
        job_id: 'test-job-id',
        status: 'deleted',
        deleted_at: '2025-11-18T10:35:00Z',
      };

      (jobApiService.deleteJob as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useDeleteJob(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        jobId: 'test-job-id',
        force: false,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(jobApiService.deleteJob).toHaveBeenCalledWith('test-job-id', false);
      expect(result.current.data).toEqual(mockResponse);
    });

    it('should delete a job with force flag', async () => {
      const mockResponse = {
        job_id: 'test-job-id',
        status: 'deleted',
        deleted_at: '2025-11-18T10:35:00Z',
      };

      (jobApiService.deleteJob as jest.Mock).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useDeleteJob(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        jobId: 'test-job-id',
        force: true,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(jobApiService.deleteJob).toHaveBeenCalledWith('test-job-id', true);
    });

    it('should handle delete job error', async () => {
      const mockError = new Error('Failed to delete job');
      (jobApiService.deleteJob as jest.Mock).mockRejectedValue(mockError);

      const { result } = renderHook(() => useDeleteJob(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        jobId: 'test-job-id',
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toEqual(mockError);
    });
  });
});
