'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { XCircle, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
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
  const t = useTranslations('jobActions');
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
        title: t('toast.cancelled'),
        description: t('toast.cancelledDescription'),
      });
      setShowCancelDialog(false);
      // Optimistically update local phase to show delete button immediately
      setLocalPhase('cancelled');
    } catch (error: any) {
      toast({
        title: t('toast.cancelFailed'),
        description: error.message || t('toast.errorDescription', { action: 'cancelling' }),
        variant: 'destructive',
      });
    }
  };

  const handleDeleteConfirm = async (force: boolean = false) => {
    try {
      await deleteMutation.mutateAsync({ jobId, force });
      toast({
        title: t('toast.deleted'),
        description: t('toast.deletedDescription'),
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
          title: t('toast.deleteFailed'),
          description: error.message || t('toast.errorDescription', { action: 'deleting' }),
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
            {cancelMutation.isPending ? t('cancelling') : t('cancelJob')}
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
            {deleteMutation.isPending ? t('deleting') : t('deleteJob')}
          </Button>
        )}
      </div>

      <ConfirmationDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        title={t('cancelDialog.title')}
        description={
          <>
            <p>{t('cancelDialog.description')}</p>
            <p className="font-semibold">{t('cancelDialog.warning')}</p>
          </>
        }
        confirmText={t('cancelDialog.confirm')}
        onConfirm={handleCancelConfirm}
        isLoading={cancelMutation.isPending}
        variant="destructive"
      />

      <ConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title={t('deleteDialog.title')}
        description={
          <>
            <p>{t('deleteDialog.description')}</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>{t('deleteDialog.items.jobData')}</li>
              <li>{t('deleteDialog.items.productImages')}</li>
              <li>{t('deleteDialog.items.videoFrames')}</li>
              <li>{t('deleteDialog.items.matchResults')}</li>
              <li>{t('deleteDialog.items.dbRecords')}</li>
            </ul>
            {isActive && (
              <p className="font-semibold text-orange-600 mt-2">
                {t('deleteDialog.activeWarning')}
              </p>
            )}
            <p className="font-semibold mt-2">{t('deleteDialog.warning')}</p>
          </>
        }
        confirmText={t('deleteDialog.confirm')}
        onConfirm={() => handleDeleteConfirm(false)}
        isLoading={deleteMutation.isPending}
        variant="destructive"
      />

      <ConfirmationDialog
        open={showForceDeleteDialog}
        onOpenChange={setShowForceDeleteDialog}
        title={t('forceDeleteDialog.title')}
        description={
          <>
            <p>{t('forceDeleteDialog.description')}</p>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>{t('forceDeleteDialog.items.cancelImmediate')}</li>
              <li>{t('forceDeleteDialog.items.deleteData')}</li>
              <li>{t('forceDeleteDialog.items.skipWait')}</li>
            </ul>
            <p className="font-semibold text-red-600 mt-2">{t('forceDeleteDialog.warning')}</p>
          </>
        }
        confirmText={t('forceDeleteDialog.confirm')}
        onConfirm={() => handleDeleteConfirm(true)}
        isLoading={deleteMutation.isPending}
        variant="destructive"
      />
    </>
  );
}
