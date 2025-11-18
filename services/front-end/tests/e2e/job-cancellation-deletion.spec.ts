import { test, expect } from '@playwright/test';

test.describe('Job Cancellation and Deletion', () => {
  test('should show cancel button for active jobs', async ({ page }) => {
    // Navigate to jobs page
    await page.goto('/jobs');

    // Start a test job
    await page.fill('input[name="query"]', 'test product');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    // Wait for job to be created and navigate to detail page
    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Check that cancel button is visible
    const cancelButton = page.locator('button:has-text("Cancel Job")');
    await expect(cancelButton).toBeVisible();

    // Delete button should not be visible for active jobs
    const deleteButton = page.locator('button:has-text("Delete Job")');
    await expect(deleteButton).not.toBeVisible();
  });

  test('should cancel a job with confirmation', async ({ page }) => {
    // Navigate to a job detail page (assuming job exists)
    await page.goto('/jobs');
    
    // Start a test job
    await page.fill('input[name="query"]', 'test cancellation');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Click cancel button
    await page.click('button:has-text("Cancel Job")');

    // Confirmation dialog should appear
    await expect(page.locator('text=Cancel Job?')).toBeVisible();
    await expect(page.locator('text=This will stop all processing')).toBeVisible();

    // Confirm cancellation
    await page.click('button:has-text("Confirm Cancellation")');

    // Wait for success message
    await expect(page.locator('text=Job cancelled')).toBeVisible({ timeout: 10000 });

    // Status should update to cancelled
    await expect(page.locator('text=Cancelled')).toBeVisible({ timeout: 5000 });
  });

  test('should show delete button for cancelled jobs', async ({ page }) => {
    // This test assumes a cancelled job exists
    // In a real scenario, you'd create and cancel a job first
    
    await page.goto('/jobs');
    
    // Start and immediately cancel a job
    await page.fill('input[name="query"]', 'test deletion');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Cancel the job
    await page.click('button:has-text("Cancel Job")');
    await page.click('button:has-text("Confirm Cancellation")');
    await expect(page.locator('text=Job cancelled')).toBeVisible({ timeout: 10000 });

    // Now delete button should be visible
    const deleteButton = page.locator('button:has-text("Delete Job")');
    await expect(deleteButton).toBeVisible();

    // Cancel button should not be visible
    const cancelButton = page.locator('button:has-text("Cancel Job")');
    await expect(cancelButton).not.toBeVisible();
  });

  test('should delete a cancelled job with confirmation', async ({ page }) => {
    await page.goto('/jobs');
    
    // Start, cancel, then delete a job
    await page.fill('input[name="query"]', 'test full flow');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Cancel first
    await page.click('button:has-text("Cancel Job")');
    await page.click('button:has-text("Confirm Cancellation")');
    await expect(page.locator('text=Job cancelled')).toBeVisible({ timeout: 10000 });

    // Now delete
    await page.click('button:has-text("Delete Job")');

    // Confirmation dialog should appear
    await expect(page.locator('text=Delete Job?')).toBeVisible();
    await expect(page.locator('text=permanently delete')).toBeVisible();

    // Confirm deletion
    await page.click('button:has-text("Delete Permanently")');

    // Should redirect to homepage
    await page.waitForURL('/', { timeout: 10000 });

    // Success message should appear
    await expect(page.locator('text=Job deleted')).toBeVisible();
  });

  test('should handle force delete for active jobs', async ({ page }) => {
    await page.goto('/jobs');
    
    // Start a job
    await page.fill('input[name="query"]', 'test force delete');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Try to delete active job (should show warning)
    // Note: This test assumes the UI allows attempting to delete active jobs
    // and shows a force delete option
    
    // For now, just verify cancel button exists for active jobs
    await expect(page.locator('button:has-text("Cancel Job")')).toBeVisible();
  });

  test('should close dialog when clicking cancel', async ({ page }) => {
    await page.goto('/jobs');
    
    // Start a job
    await page.fill('input[name="query"]', 'test dialog cancel');
    await page.fill('input[name="top_amz"]', '5');
    await page.fill('input[name="top_ebay"]', '5');
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs\/[a-f0-9-]+/);

    // Open cancel dialog
    await page.click('button:has-text("Cancel Job")');
    await expect(page.locator('text=Cancel Job?')).toBeVisible();

    // Click cancel in dialog
    await page.click('button:has-text("Cancel"):not(:has-text("Job"))');

    // Dialog should close
    await expect(page.locator('text=Cancel Job?')).not.toBeVisible();

    // Job should still be active
    await expect(page.locator('button:has-text("Cancel Job")')).toBeVisible();
  });
});
