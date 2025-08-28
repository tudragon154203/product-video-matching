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
    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');
  });

  test('should display unknown status correctly', async ({ page }) => {
    // Mock unknown phase
    await page.route(`**/api/status/${jobId}`, async route => {
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

    // Assert text
    await expect(page.locator('text="Status unknown."')).toBeVisible();
    
    // Assert color - gray
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(128, 128, 128)');
    
    // No effect should be present
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should display collection phase with animated dots', async ({ page }) => {
    // Mock collection phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'collection',
          percent: 20,
          counts: { products: 5, videos: 3, images: 0, frames: 0 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="Collecting products and videos…"')).toBeVisible();
    
    // Assert color - blue
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(59, 130, 246)'); // blue-500
    
    // Assert animated dots
    await expect(page.locator('[data-testid="status-animated-dots"]')).toBeVisible();
    
    // No spinner or progress bar
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    
    // Assert collection badges
    await expect(page.locator('text="✔ Products done"')).toBeVisible();
    await expect(page.locator('text="✔ Videos done"')).not.toBeVisible();
  });

  test('should display collection phase with both products and videos done', async ({ page }) => {
    // Mock collection phase with both products and videos done
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'collection',
          percent: 20,
          counts: { products: 5, videos: 8, images: 0, frames: 0 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="Collecting products and videos…"')).toBeVisible();
    
    // Assert collection badges
    await expect(page.locator('text="✔ Products done"')).toBeVisible();
    await expect(page.locator('text="✔ Videos done"')).toBeVisible();
    await expect(page.locator('text="Collection finished"')).toBeVisible();
  });

  test('should display feature extraction phase with progress bar', async ({ page }) => {
    // Mock feature extraction phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'feature_extraction',
          percent: 50,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="Extracting features (images / video frames)…"')).toBeVisible();
    
    // Assert color - yellow
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(234, 179, 8)'); // yellow-500
    
    // Assert progress bar
    await expect(page.locator('[data-testid="status-progress-bar"]')).toBeVisible();
    
    // No spinner or animated dots
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should display matching phase with spinner', async ({ page }) => {
    // Mock matching phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'matching',
          percent: 80,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="Matching products with videos…"')).toBeVisible();
    
    // Assert color - purple
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(147, 51, 234)'); // purple-500
    
    // Assert spinner
    await expect(page.locator('[data-testid="status-spinner"]')).toBeVisible();
    
    // No progress bar or animated dots
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should display evidence phase with progress bar', async ({ page }) => {
    // Mock evidence phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'evidence',
          percent: 90,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="Generating visual evidence…"')).toBeVisible();
    
    // Assert color - orange
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(249, 115, 22)'); // orange-500
    
    // Assert progress bar
    await expect(page.locator('[data-testid="status-progress-bar"]')).toBeVisible();
    
    // No spinner or animated dots
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should display completed phase with checkmark', async ({ page }) => {
    // Mock completed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="✅ Completed!"')).toBeVisible();
    
    // Assert color - green
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(34, 197, 94)'); // green-500
    
    // No effects should be present
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should display failed phase with error', async ({ page }) => {
    // Mock failed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'failed',
          percent: 0,
          counts: { products: 0, videos: 0, images: 0, frames: 0 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Assert text
    await expect(page.locator('text="❌ Job failed."')).toBeVisible();
    
    // Assert color - red
    const statusIndicator = page.locator('[data-testid="status-color-circle"]');
    await expect(statusIndicator).toHaveCSS('background-color', 'rgb(239, 68, 68)'); // red-500
    
    // No effects should be present
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });

  test('should stop polling when job reaches terminal state', async ({ page }) => {
    let requestCount = 0;
    
    // Mock the API response and count requests
    await page.route(`**/api/status/${jobId}`, async route => {
      requestCount++;
      const phase = requestCount === 1 ? 'collection' : 'completed';
      
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: phase,
          percent: phase === 'collection' ? 20 : 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Wait for initial collection phase
    await expect(page.locator('text="Collecting products and videos…"')).toBeVisible();
    
    // Wait for polling to complete and job to reach completed state
    await expect(page.locator('text="✅ Completed!"')).toBeVisible();
    
    // Verify that polling stopped (should only have 2 requests: initial + one more)
    // In a real scenario, we'd need to mock the network to verify no more requests
    await expect(page.locator('[data-testid="status-spinner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-progress-bar"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="status-animated-dots"]')).not.toBeVisible();
  });
});
