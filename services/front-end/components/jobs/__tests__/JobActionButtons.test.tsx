import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JobActionButtons } from '../JobActionButtons';
import { useCancelJob, useDeleteJob } from '@/lib/api/hooks';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/ui/use-toast';

// Mock dependencies
jest.mock('@/lib/api/hooks');
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));
jest.mock('@/components/ui/use-toast');

const mockUseCancelJob = useCancelJob as jest.MockedFunction<typeof useCancelJob>;
const mockUseDeleteJob = useDeleteJob as jest.MockedFunction<typeof useDeleteJob>;
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;

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

describe('JobActionButtons', () => {
  const mockPush = jest.fn();
  const mockToast = jest.fn();
  const mockCancelMutate = jest.fn();
  const mockDeleteMutate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    mockUseRouter.mockReturnValue({
      push: mockPush,
    } as any);

    mockUseToast.mockReturnValue({
      toast: mockToast,
    } as any);

    mockUseCancelJob.mockReturnValue({
      mutateAsync: mockCancelMutate,
      isPending: false,
    } as any);

    mockUseDeleteJob.mockReturnValue({
      mutateAsync: mockDeleteMutate,
      isPending: false,
    } as any);
  });

  describe('Button Visibility', () => {
    it('should show cancel button for collection phase', () => {
      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Cancel Job')).toBeInTheDocument();
      expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
    });

    it('should show cancel button for feature_extraction phase', () => {
      render(<JobActionButtons jobId="test-job" phase="feature_extraction" />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Cancel Job')).toBeInTheDocument();
      expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
    });

    it('should show cancel button for matching phase', () => {
      render(<JobActionButtons jobId="test-job" phase="matching" />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Cancel Job')).toBeInTheDocument();
      expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
    });

    it('should show cancel button for evidence phase', () => {
      render(<JobActionButtons jobId="test-job" phase="evidence" />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Cancel Job')).toBeInTheDocument();
      expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
    });

    it('should show delete button for completed phase', () => {
      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      expect(screen.queryByText('Cancel Job')).not.toBeInTheDocument();
      expect(screen.getByText('Delete Job')).toBeInTheDocument();
    });

    it('should show delete button for failed phase', () => {
      render(<JobActionButtons jobId="test-job" phase="failed" />, {
        wrapper: createWrapper(),
      });

      expect(screen.queryByText('Cancel Job')).not.toBeInTheDocument();
      expect(screen.getByText('Delete Job')).toBeInTheDocument();
    });

    it('should show delete button for cancelled phase', () => {
      render(<JobActionButtons jobId="test-job" phase="cancelled" />, {
        wrapper: createWrapper(),
      });

      expect(screen.queryByText('Cancel Job')).not.toBeInTheDocument();
      expect(screen.getByText('Delete Job')).toBeInTheDocument();
    });

    it('should show nothing for unknown phase', () => {
      render(<JobActionButtons jobId="test-job" phase="unknown" />, {
        wrapper: createWrapper(),
      });

      expect(screen.queryByText('Cancel Job')).not.toBeInTheDocument();
      expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
    });
  });

  describe('Cancel Job Flow', () => {
    it('should open confirmation dialog when cancel button is clicked', () => {
      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Cancel Job'));

      expect(screen.getByText('Cancel Job?')).toBeInTheDocument();
      expect(screen.getByText(/stop all processing/i)).toBeInTheDocument();
    });

    it('should close dialog when cancel is clicked in dialog', async () => {
      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Cancel Job'));
      expect(screen.getByText('Cancel Job?')).toBeInTheDocument();

      const cancelButtons = screen.getAllByText('Cancel');
      const dialogCancelButton = cancelButtons.find(btn => btn.tagName === 'BUTTON');
      if (dialogCancelButton) {
        fireEvent.click(dialogCancelButton);
      }

      await waitFor(() => {
        expect(screen.queryByText('Cancel Job?')).not.toBeInTheDocument();
      });
    });

    it('should call cancel mutation when confirmed', async () => {
      mockCancelMutate.mockResolvedValue({
        job_id: 'test-job',
        phase: 'cancelled',
        cancelled_at: '2025-11-18T10:30:00Z',
        reason: 'user_request',
      });

      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Cancel Job'));
      fireEvent.click(screen.getByText('Confirm Cancellation'));

      await waitFor(() => {
        expect(mockCancelMutate).toHaveBeenCalledWith({ jobId: 'test-job' });
      });
    });

    it('should show success toast after successful cancellation', async () => {
      mockCancelMutate.mockResolvedValue({
        job_id: 'test-job',
        phase: 'cancelled',
        cancelled_at: '2025-11-18T10:30:00Z',
        reason: 'user_request',
      });

      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Cancel Job'));
      fireEvent.click(screen.getByText('Confirm Cancellation'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Job cancelled',
          description: 'The job has been cancelled successfully.',
        });
      });
    });

    it('should show error toast on cancellation failure', async () => {
      mockCancelMutate.mockRejectedValue(new Error('Network error'));

      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Cancel Job'));
      fireEvent.click(screen.getByText('Confirm Cancellation'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Failed to cancel job',
          description: 'Network error',
          variant: 'destructive',
        });
      });
    });

    it('should disable button during cancellation', () => {
      mockUseCancelJob.mockReturnValue({
        mutateAsync: mockCancelMutate,
        isPending: true,
      } as any);

      render(<JobActionButtons jobId="test-job" phase="collection" />, {
        wrapper: createWrapper(),
      });

      const button = screen.getByText('Cancelling...');
      expect(button).toBeDisabled();
    });
  });

  describe('Delete Job Flow', () => {
    it('should open confirmation dialog when delete button is clicked', () => {
      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));

      expect(screen.getByText('Delete Job?')).toBeInTheDocument();
      expect(screen.getByText(/permanently delete/i)).toBeInTheDocument();
    });

    it('should close dialog when cancel is clicked in dialog', async () => {
      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      expect(screen.getByText('Delete Job?')).toBeInTheDocument();

      const cancelButtons = screen.getAllByText('Cancel');
      const dialogCancelButton = cancelButtons.find(btn => btn.tagName === 'BUTTON');
      if (dialogCancelButton) {
        fireEvent.click(dialogCancelButton);
      }

      await waitFor(() => {
        expect(screen.queryByText('Delete Job?')).not.toBeInTheDocument();
      });
    });

    it('should call delete mutation when confirmed', async () => {
      mockDeleteMutate.mockResolvedValue({
        job_id: 'test-job',
        status: 'deleted',
        deleted_at: '2025-11-18T10:35:00Z',
      });

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(mockDeleteMutate).toHaveBeenCalledWith({
          jobId: 'test-job',
          force: false,
        });
      });
    });

    it('should redirect to jobs list after successful deletion', async () => {
      mockDeleteMutate.mockResolvedValue({
        job_id: 'test-job',
        status: 'deleted',
        deleted_at: '2025-11-18T10:35:00Z',
      });

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/');
      });
    });

    it('should show success toast after successful deletion', async () => {
      mockDeleteMutate.mockResolvedValue({
        job_id: 'test-job',
        status: 'deleted',
        deleted_at: '2025-11-18T10:35:00Z',
      });

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Job deleted',
          description: 'The job has been deleted successfully.',
        });
      });
    });

    it('should show force delete dialog on 409 error', async () => {
      mockDeleteMutate.mockRejectedValue({ status: 409 });

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(screen.getByText('Force Delete Active Job?')).toBeInTheDocument();
      });
    });

    it('should call delete with force=true when force delete is confirmed', async () => {
      mockDeleteMutate
        .mockRejectedValueOnce({ status: 409 })
        .mockResolvedValueOnce({
          job_id: 'test-job',
          status: 'deleted',
          deleted_at: '2025-11-18T10:35:00Z',
        });

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(screen.getByText('Force Delete Active Job?')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Force Delete'));

      await waitFor(() => {
        expect(mockDeleteMutate).toHaveBeenCalledWith({
          jobId: 'test-job',
          force: true,
        });
      });
    });

    it('should show error toast on deletion failure', async () => {
      mockDeleteMutate.mockRejectedValue(new Error('Server error'));

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      fireEvent.click(screen.getByText('Delete Job'));
      fireEvent.click(screen.getByText('Delete Permanently'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith({
          title: 'Failed to delete job',
          description: 'Server error',
          variant: 'destructive',
        });
      });
    });

    it('should disable button during deletion', () => {
      mockUseDeleteJob.mockReturnValue({
        mutateAsync: mockDeleteMutate,
        isPending: true,
      } as any);

      render(<JobActionButtons jobId="test-job" phase="completed" />, {
        wrapper: createWrapper(),
      });

      const button = screen.getByText('Deleting...');
      expect(button).toBeDisabled();
    });
  });
});
