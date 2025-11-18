# Front-End — Job Cancellation & Deletion PRD

## 1. Background & Problem
Users currently have no way to stop a running job or delete completed/failed jobs from the UI. When a job is stuck, malfunctioning, or no longer needed, operators must manually intervene via backend tools. Similarly, test jobs and unwanted results accumulate in the job list with no cleanup mechanism. We need to expose cancel and delete actions in the front-end that integrate with the new `main-api` endpoints (`POST /jobs/{job_id}/cancel` and `DELETE /jobs/{job_id}`).

## 2. Goals
1. **Cancel running jobs** – provide a clear UI action to stop in-progress jobs, with confirmation dialog and real-time status updates.
2. **Delete jobs** – allow users to remove completed, failed, or cancelled jobs from the system, including all associated data.
3. **User safety** – prevent accidental cancellations/deletions with confirmation dialogs that explain consequences.
4. **Status feedback** – show loading states, success/error messages, and handle edge cases (already cancelled, deletion in progress, etc.).
5. **Responsive updates** – reflect cancellation/deletion state changes immediately in job lists and detail views.

## 3. Non-Goals
- Bulk cancel/delete operations (future enhancement).
- Job pause/resume functionality (not supported by backend).
- Undo/rollback after cancellation or deletion.
- Automatic job expiry policies (backend concern).

## 4. Users & Use Cases
- **Operator**: Cancels a stuck job that's consuming resources unnecessarily.
- **Developer**: Deletes test jobs after validating new features.
- **Customer Success**: Removes jobs containing sensitive test data at customer request.
- **Power User**: Cleans up failed jobs to keep their workspace organized.

## 5. Functional Requirements

### 5.1 Cancel Job Button
**Location**: Job detail page (when viewing a specific job)

**Visibility Rules**:
- Show "Cancel Job" button only when `job.phase` is one of: `collection`, `feature_extraction`, `matching`, `evidence`
- Hide button when phase is: `completed`, `failed`, `cancelled`
- Disable button during cancellation request (show loading state)

**Interaction Flow**:
1. User clicks "Cancel Job" button
2. Show confirmation dialog:
   ```
   Title: Cancel Job?
   Message: This will stop all processing for this job. Workers will be notified 
            to stop, and queued tasks will be removed. This action cannot be undone.
   
   Optional: [Text input for cancellation reason]
   
   Buttons: [Cancel] [Confirm Cancellation]
   ```
3. On confirm:
   - Send `POST /jobs/{job_id}/cancel` with optional reason
   - Show loading spinner on button
   - Disable all job actions during request
4. On success (200/202):
   - Update job phase to `cancelled` in UI
   - Show success toast: "Job cancelled successfully"
   - Refresh job status to get latest state
   - Update button to show "Cancelled" (disabled state)
5. On error:
   - Show error toast with message from API
   - Re-enable cancel button
   - Log error details for debugging

**API Integration**:
```typescript
// Request
POST /jobs/{job_id}/cancel
Content-Type: application/json
{
  "reason": "user_request",  // Optional, defaults to "user_request"
  "notes": "User-provided reason (optional)"  // Optional
}

// Response (200) - Success
{
  "job_id": "uuid",
  "phase": "cancelled",
  "cancelled_at": "2025-11-18T10:30:00Z",
  "reason": "user_request",
  "notes": "User-provided reason (optional)"
}

// Response (404) - Job not found
{
  "detail": "Job not found"
}

// Note: Backend handles idempotency - calling cancel on already cancelled job returns existing cancellation info
// Jobs already in "completed" or "failed" state return 200 with current state and appropriate message
```

**UI States**:
- **Default**: Red/orange "Cancel Job" button with warning icon
- **Loading**: Button shows spinner, text "Cancelling..."
- **Success**: Button becomes "Cancelled" (disabled, grey)
- **Error**: Button returns to default, error message shown

### 5.2 Delete Job Button
**Location**: 
- Job detail page (primary location)
- Job list page (optional, as action menu item per job)

**Visibility Rules**:
- Show "Delete Job" button when `job.phase` is one of: `completed`, `failed`, `cancelled`
- For active jobs (`collection`, `feature_extraction`, `matching`, `evidence`), show "Cancel & Delete" option
- Hide during deletion request

**Interaction Flow**:
1. User clicks "Delete Job" button
2. Show confirmation dialog:
   ```
   Title: Delete Job?
   Message: This will permanently delete:
            • All job data and metadata
            • Product images and masks
            • Video frames and keyframes
            • Match results and evidence
            • All associated database records
   
   For active jobs: "This job is still running. It will be cancelled first, 
                     then deleted after workers acknowledge."
   
   Warning: This action cannot be undone.
   
   Buttons: [Cancel] [Delete Permanently]
   ```
3. On confirm:
   - Send `DELETE /jobs/{job_id}?force=false`
   - Show loading overlay on job detail page
   - Disable all interactions
4. On success (200):
   - Show success toast: "Job deleted successfully"
   - Redirect to job list page
   - Remove job from list if currently visible
5. On error (409 - job in progress):
   - Show dialog: "Job is still running. Cancel it first or use force delete?"
   - Offer "Force Delete" option that retries with `?force=true`
6. On error (other):
   - Show error toast with API message
   - Keep job visible, re-enable delete button

**API Integration**:
```typescript
// Request
DELETE /jobs/{job_id}?force=false

// Response (200) - Deletion successful
{
  "job_id": "uuid",
  "status": "deleted",
  "deleted_at": "2025-11-18T10:35:00Z"
}

// Response (404) - Job not found
{
  "detail": "Job not found"
}

// Response (409) - Job in progress, force required
{
  "detail": "Job is still active. Cancel it first or use force=true"
}

// Note: Backend automatically cancels active jobs when force=true is used
// Deletion is synchronous (no 202 async response in current implementation)
```

**UI States**:
- **Default**: Red "Delete Job" button with trash icon
- **Loading**: Button shows spinner, text "Deleting..." (deletion is synchronous)
- **Success**: Redirect to job list
- **Error**: Error message, button re-enabled

### 5.3 Job List Integration
**Updates Needed**:
- Add action menu (three-dot menu) to each job card/row
- Menu items based on job phase:
  - Active jobs: "Cancel Job", "View Details"
  - Completed/Failed/Cancelled: "Delete Job", "View Details"
- Show visual indicators for cancelled jobs (grey badge, strikethrough, etc.)
- Real-time updates when jobs are cancelled/deleted (via polling or WebSocket if available)

### 5.4 Job Detail Page Updates
**Layout Changes**:
- Add action buttons in header area (next to job title or in top-right corner)
- Button group: `[Cancel Job] [Delete Job]` (visibility based on phase)
- Show cancellation metadata when present:
  ```
  Status: Cancelled
  Cancelled at: 2025-11-18 10:30:00
  Reason: user_request
  Notes: Customer requested stop
  ```
- Show deletion warning banner for cancelled jobs: "This job was cancelled. You can delete it to free up storage."

### 5.5 Confirmation Dialogs
**Design Requirements**:
- Modal overlay with clear title and message
- Destructive actions use red/warning colors
- Explain consequences in plain language
- Optional reason input for cancellation (textarea, max 500 chars)
- Two-button layout: secondary "Cancel" (left), primary destructive action (right)
- Keyboard support: ESC to cancel, Enter to confirm (with focus management)
- Prevent accidental double-clicks (disable buttons after first click)

### 5.6 Error Handling
**Common Error Scenarios**:
1. **Network failure**: Show retry option, don't lose user input
2. **Job already cancelled**: Show info message, update UI to reflect current state
3. **Job already deleted**: Redirect to job list with info toast
4. **Insufficient permissions**: Show error, suggest contacting admin
5. **Cancellation pending**: Show status, offer to wait or navigate away
6. **Deletion timeout**: Show progress, offer to check status later

**Error Message Examples**:
- "Failed to cancel job. Please try again."
- "This job has already been cancelled."
- "Unable to delete job. It may still be processing. Try again in a moment."
- "Deletion is taking longer than expected. Check back in a few minutes."

### 5.7 Loading & Feedback States
**Visual Indicators**:
- Button spinners during API calls
- Disabled state for all actions during operations
- Toast notifications for success/error (auto-dismiss after 5s)
- Progress indicators for async operations
- Skeleton loaders when refreshing job status

**Accessibility**:
- ARIA labels for all buttons and states
- Screen reader announcements for status changes
- Focus management in dialogs
- Keyboard navigation support

## 6. UI/UX Specifications

### 6.1 Button Styles
```typescript
// Cancel Job Button
<Button
  variant="destructive-outline"
  icon={<XCircleIcon />}
  disabled={isCancelling || !canCancel}
  onClick={handleCancelClick}
>
  {isCancelling ? 'Cancelling...' : 'Cancel Job'}
</Button>

// Delete Job Button
<Button
  variant="destructive"
  icon={<TrashIcon />}
  disabled={isDeleting || !canDelete}
  onClick={handleDeleteClick}
>
  {isDeleting ? 'Deleting...' : 'Delete Job'}
</Button>
```

### 6.2 Confirmation Dialog Component
```typescript
interface ConfirmationDialogProps {
  title: string;
  message: string;
  confirmText: string;
  confirmVariant: 'destructive' | 'warning';
  onConfirm: () => void;
  onCancel: () => void;
  showReasonInput?: boolean;
  isLoading?: boolean;
}
```

### 6.3 Job Status Badge Updates
Add new badge variant for cancelled jobs:
```typescript
// Existing: completed (green), failed (red), in-progress (blue)
// New: cancelled (grey/orange)
<Badge variant="cancelled">Cancelled</Badge>
```

## 7. Technical Implementation

### 7.1 API Client Methods
```typescript
// services/api/jobs.ts

export async function cancelJob(
  jobId: string,
  reason?: string,
  notes?: string
): Promise<CancelJobResponse> {
  const response = await fetch(`/api/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, notes }),
  });
  
  if (!response.ok) {
    throw new Error(await response.text());
  }
  
  return response.json();
}

export async function deleteJob(
  jobId: string,
  force: boolean = false
): Promise<DeleteJobResponse> {
  const response = await fetch(
    `/api/jobs/${jobId}?force=${force}`,
    { method: 'DELETE' }
  );
  
  if (!response.ok) {
    if (response.status === 409) {
      const errorData = await response.json();
      throw new JobInProgressError(errorData.detail);
    }
    if (response.status === 404) {
      throw new JobNotFoundError('Job not found');
    }
    throw new Error(await response.text());
  }
  
  return response.json();
}
```

### 7.2 React Hooks
```typescript
// hooks/useJobActions.ts

export function useJobActions(jobId: string) {
  const [isCancelling, setIsCancelling] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const cancelJob = async (reason?: string, notes?: string) => {
    setIsCancelling(true);
    try {
      const result = await api.cancelJob(jobId, reason, notes);
      toast.success('Job cancelled successfully');
      return result;
    } catch (error) {
      toast.error(`Failed to cancel job: ${error.message}`);
      throw error;
    } finally {
      setIsCancelling(false);
    }
  };
  
  const deleteJob = async (force: boolean = false) => {
    setIsDeleting(true);
    try {
      const result = await api.deleteJob(jobId, force);
      toast.success('Job deleted successfully');
      return result;
    } catch (error) {
      if (error instanceof JobInProgressError) {
        // Handle 409 - offer force delete
        return { needsForce: true, error: error.message };
      }
      if (error instanceof JobNotFoundError) {
        toast.info('Job not found or already deleted');
        return { alreadyDeleted: true };
      }
      toast.error(`Failed to delete job: ${error.message}`);
      throw error;
    } finally {
      setIsDeleting(false);
    }
  };
  
  return { cancelJob, deleteJob, isCancelling, isDeleting };
}
```

### 7.3 State Management
```typescript
// Update job state after cancellation
const handleJobCancelled = (jobId: string, cancelledData: CancelJobResponse) => {
  // Update in job list
  updateJobInList(jobId, {
    phase: 'cancelled',
    cancelled_at: cancelledData.cancelled_at,
    cancellation_reason: cancelledData.reason,
  });
  
  // Update in detail view if open
  if (currentJobId === jobId) {
    setCurrentJob(prev => ({
      ...prev,
      phase: 'cancelled',
      cancelled_at: cancelledData.cancelled_at,
    }));
  }
};

// Remove job after deletion
const handleJobDeleted = (jobId: string) => {
  removeJobFromList(jobId);
  
  if (currentJobId === jobId) {
    navigate('/jobs');
  }
};
```

### 7.4 Polling for Async Deletion
```typescript
async function pollJobDeletion(
  jobId: string,
  maxAttempts: number = 30,
  intervalMs: number = 2000
): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, intervalMs));
    
    try {
      await api.getJob(jobId);
      // Job still exists, continue polling
    } catch (error) {
      if (error.status === 404) {
        // Job deleted successfully
        return;
      }
      throw error;
    }
  }
  
  throw new Error('Deletion timeout - job may still be processing');
}
```

## 8. Testing Plan

### 8.1 Unit Tests
- `useJobActions` hook: cancel/delete logic, error handling, loading states
- API client methods: request formatting, response parsing, error cases
- Confirmation dialog: user interactions, keyboard support, validation

### 8.2 Integration Tests
- Cancel job flow: button click → dialog → API call → UI update
- Delete job flow: button click → dialog → API call → redirect
- Error scenarios: network failures, 409 conflicts, already cancelled/deleted
- Async deletion: polling logic, timeout handling, status updates

### 8.3 E2E Tests (Playwright)
```typescript
// tests/e2e/job-cancellation.spec.ts

test('cancel running job', async ({ page }) => {
  // Start a job
  const jobId = await startTestJob(page);
  
  // Navigate to job detail
  await page.goto(`/jobs/${jobId}`);
  
  // Click cancel button
  await page.click('button:has-text("Cancel Job")');
  
  // Confirm in dialog
  await page.fill('textarea[name="reason"]', 'Test cancellation');
  await page.click('button:has-text("Confirm Cancellation")');
  
  // Verify UI updates
  await expect(page.locator('text=Cancelled')).toBeVisible();
  await expect(page.locator('button:has-text("Cancel Job")')).toBeDisabled();
});

test('delete completed job', async ({ page }) => {
  const jobId = await createCompletedJob();
  
  await page.goto(`/jobs/${jobId}`);
  await page.click('button:has-text("Delete Job")');
  await page.click('button:has-text("Delete Permanently")');
  
  // Should redirect to job list
  await expect(page).toHaveURL('/jobs');
  
  // Job should not appear in list
  await expect(page.locator(`[data-job-id="${jobId}"]`)).not.toBeVisible();
});

test('force delete active job', async ({ page }) => {
  const jobId = await startTestJob(page);
  
  await page.goto(`/jobs/${jobId}`);
  await page.click('button:has-text("Delete Job")');
  
  // Should show warning about active job
  await expect(page.locator('text=still running')).toBeVisible();
  
  await page.click('button:has-text("Delete Permanently")');
  
  // Should handle 409 and offer force option
  await expect(page.locator('text=Force Delete')).toBeVisible();
  await page.click('button:has-text("Force Delete")');
  
  await expect(page).toHaveURL('/jobs');
});
```

## 9. Accessibility Requirements
- All buttons have descriptive ARIA labels
- Confirmation dialogs trap focus and announce to screen readers
- Keyboard navigation: Tab, Enter, Escape
- Color contrast meets WCAG AA standards
- Loading states announced to screen readers
- Error messages associated with form controls

## 10. Performance Considerations
- Debounce rapid button clicks (prevent double-submit)
- Optimistic UI updates where safe (show cancelled state immediately)
- Efficient polling: exponential backoff for async deletion
- Cancel in-flight requests if user navigates away
- Lazy load confirmation dialogs (code splitting)

## 11. Security & Authorization
- Reuse existing auth tokens for API calls
- Handle 401/403 responses gracefully
- Don't expose sensitive job data in error messages
- Validate user permissions before showing action buttons
- Log all cancel/delete actions for audit trail (backend handles this)

## 12. Rollout Plan
1. **Phase 1**: Implement cancel button on job detail page (feature flag)
2. **Phase 2**: Add delete button for completed/failed jobs
3. **Phase 3**: Integrate into job list with action menus
4. **Phase 4**: Add bulk operations (future sprint)

## 13. Open Questions
- Should we show a "Recently Deleted" view with restore option? (Not in scope - backend hard-deletes)
- Do we need admin-only vs user permissions for these actions? (Reuse existing auth)
- Should cancellation reason be required or optional? (Optional for now)
- How long should we poll for async deletion before timing out? (60 seconds)

## 14. Dependencies
- Backend: `main-api` sprint 3 endpoints must be deployed first
- Design: Confirmation dialog component (can reuse existing modal)
- Auth: Existing authentication system
- Routing: React Router for navigation after deletion

## 15. Success Metrics
- Cancel success rate (target: >95%)
- Delete success rate (target: >95%)
- Average time to cancel/delete (target: <3 seconds for immediate operations)
- User error rate (accidental cancellations - should be low with confirmation)
- Support tickets related to stuck jobs (should decrease)
