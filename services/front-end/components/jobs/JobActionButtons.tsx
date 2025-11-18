'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { XCircle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useCancelJob, useDeleteJob } from '@/lib/api/hooks';
import { ConfirmationDialog } from './ConfirmationDialog';
import { useToast } from '@/components/ui/use-toast';
import type { Phase } from '@/lib/zod/job';

interface JobActionButtonsProps {
  jobId: string;
  phase: Phase;
}

export function JobActionButtons({ jobId, phase }: JobActionButtonsProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showForceDeleteDialog, setShowForceDeleteDialog] = useState(false);
  const [localPhase, setLocalPhase] = useState<Phase>(phase);

  const cancelMutation = useCancelJob();
  const deleteMutation = useDeleteJob();

  // Use local phase if it's been updated, otherwise use prop
  const currentPhase = localPhase === 'cancelled' ? localPhase : phase;

  const canCancel = ['collection', 'feature_extraction', 'matching', 'evidence'].includes(currentPhase);
  const canDelete = ['completed', 'failed', 'cancelled'].includes(currentPhase);
  const isActive = ['collection', 'feature_extraction', 'matching', 'evidence'].includes(currentPhase);

  const handleCancelConfirm = async () => {
    try {
      await cancelMutation.mutateAsync({ jobId });
      toast({
        title: 'Job cancelled',
        description: 'The job has been cancelled successfully.',
      });
      setShowCancelDialog(false);
      // Optimistically update local phase to show delete button immediately
      setLocalPhase('cancelled');
    } catch (error: any) {
      toast({
        title: 'Failed to cancel job',
        description: error.message || 'An error occurred while cancelling the job.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteConfirm = async (force: boolean = false) => {
    try {
      await deleteMutation.mutateAsync({ jobId, force });
      toast({
        title: 'Job deleted',
        description: 'The job has been deleted successfully.',
      });
      setShowDeleteDialog(false);
      setShowForceDeleteDialog(false);
      router.push('/');
    } catch (error: any) {
      if (error.status === 409 && !force) {
        setShowDeleteDialog(false);
        setShowForceDeleteDialog(true);
      } else {
        toast({
          title: 'Failed to delete job',
          description: error.message || 'An error occurred while deleting the job.',
          variant: 'destructive',
        });
      }
    }
  };

  if (!canCancel && !canDelete) {
    return null;
  }

  return (
    <>
      <div className="flex gap-2">
        {canCancel && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCancelDialog(true)}
            disabled={cancelMutation.isPending}
            className="text-orange-600 hover:text-orange-700 hover:bg-orange-50"
          >
            <XCircle className="h-4 w-4 mr-2" />
            {cancelMutation.isPending ? 'Cancelling...' : 'Cancel Job'}
          </Button>
        )}

        {canDelete && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
            disabled={deleteMutation.isPending}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {deleteMutation.isPending ? 'Deleting...' : 'Delete Job'}
          </Button>
        )}
      </div>

      <ConfirmationDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        title="Cancel Job?"
        description={
          <>
            <p>This will stop all processing for this job. Workers will be notified to stop, and queued tasks will be removed.</p>
            <p className="font-semibold">This action cannot be undone.</p>
          </>
        }
        confirmText="Confirm Cancellation"
        onConfirm={handleCancelConfirm}
        isLoading={cancelMutation.isPending}
        variant="destructive"
      />

      <ConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Job?"
        description={
          <>
            <p>This will permanently delete:</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>All job data and metadata</li>
              <li>Product images and masks</li>
              <li>Video frames and keyframes</li>
              <li>Match results and evidence</li>
              <li>All associated database records</li>
            </ul>
            {isActive && (
              <p className="font-semibold text-orange-600 mt-2">
                This job is still running. It will be cancelled first, then deleted after workers acknowledge.
              </p>
            )}
            <p className="font-semibold mt-2">This action cannot be undone.</p>
          </>
        }
        confirmText="Delete Permanently"
        onConfirm={() => handleDeleteConfirm(false)}
        isLoading={deleteMutation.isPending}
        variant="destructive"
      />

      <ConfirmationDialog
        open={showForceDeleteDialog}
        onOpenChange={setShowForceDeleteDialog}
        title="Force Delete Active Job?"
        description={
          <>
            <p>This job is still in progress. Force delete will:</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>Cancel the job immediately</li>
              <li>Delete all associated data</li>
              <li>Skip waiting for worker acknowledgement</li>
            </ul>
            <p className="font-semibold text-red-600 mt-2">This is a forceful operation and cannot be undone.</p>
          </>
        }
        confirmText="Force Delete"
        onConfirm={() => handleDeleteConfirm(true)}
        isLoading={deleteMutation.isPending}
        variant="destructive"
      />
    </>
  );
}
