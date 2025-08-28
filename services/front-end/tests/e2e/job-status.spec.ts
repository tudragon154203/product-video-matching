import { test, expect } from '@playwright/test';

test.describe('Job Status Line Display', () => {
  const jobId = 'test-job-id';

  test.beforeEach(async ({ page }) => {
    // Mock the API response for job status
    await page.route(`**/api/status/${jobId}`, async route => {
      // Default to unknown phase for initial setup
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'unknown',
          percent: 0,
          counts: { products: 0, videos: 0, images: 0, frames: 0 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Navigate to a page where JobItemRow is likely rendered, e.g., a job details page
    // Assuming there's a route like /jobs/:jobId that displays job details
    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');
  });

  test('should display unknown status correctly', async ({ page }) => {
    // Assert text
    await expect(page.locator('text="Status unknown."')).toBeVisible();
    
    // Assert color (this might need adjustment based on actual CSS)
    // Assuming the color is applied to a specific element, e.g., a div with a class
    const statusIndicator = page.locator('.h-2.w-2.rounded-full'); // Selector from job-item-row.tsx
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(128, 128, 128)'); // Gray color
  });
});
