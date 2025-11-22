import { test, expect } from '@playwright/test';

test.describe('Completed Job Display', () => {
  const jobId = 'test-completed-job';

  test.beforeEach(async ({ page }) => {
    // Mock job details API
    await page.route(`**/api/jobs/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          query: 'ergonomic pillows',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock products API
    await page.route(`**/api/jobs/${jobId}/products*`, async route => {
      await route.fulfill({
        json: {
          items: [],
          total: 5,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      });
    });

    // Mock videos API
    await page.route(`**/api/jobs/${jobId}/videos*`, async route => {
      await route.fulfill({
        json: {
          items: [],
          total: 8,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      });
    });
  });

  test('should display completion banner with matches found', async ({ page }) => {
    // Mock completed phase with matches
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary with matches
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert completion banner is visible
    await expect(page.locator('text="✅ Completed!"')).toBeVisible();
    await expect(page.locator('text="Job completed successfully with 12 matches found."')).toBeVisible();

    // Assert banner has green styling
    const banner = page.locator('div').filter({ hasText: /✅.*Completed/ }).first();
    await expect(banner).toHaveClass(/bg-green-50/);
  });

  test('should display completion banner with no matches', async ({ page }) => {
    // Mock completed phase without matches
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary with no matches
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 0,
          pairs_processed: 40,
          evidence_ready: 0,
          avg_score: null,
          p90_score: null,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert completion banner shows no matches message
    await expect(page.locator('text="✅ Completed!"')).toBeVisible();
    await expect(page.locator('text="Job completed successfully. No matches were found."')).toBeVisible();
  });

  test('should display matching panel for completed job', async ({ page }) => {
    // Mock completed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert matching panel is visible
    await expect(page.locator('text="Matches Found"')).toBeVisible();
    await expect(page.locator('text="12"')).toBeVisible();
    await expect(page.locator('text="Evidence Ready"')).toBeVisible();
  });

  test('should display feature extraction panel for completed job', async ({ page }) => {
    // Mock completed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert feature extraction panel is visible
    await expect(page.locator('text="Product Images"')).toBeVisible();
    await expect(page.locator('text="Video Frames"')).toBeVisible();
    await expect(page.locator('text="10 total images"')).toBeVisible();
    await expect(page.locator('text="15 total frames"')).toBeVisible();
  });

  test('should not show progress banners for completed job', async ({ page }) => {
    // Mock completed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert no progress banners are shown
    await expect(page.locator('text="Feature extraction in progress"')).not.toBeVisible();
    await expect(page.locator('text="Matching in progress"')).not.toBeVisible();
    await expect(page.locator('text="Generating visual evidence"')).not.toBeVisible();
  });

  test('should stop polling when job is completed', async ({ page }) => {
    let requestCount = 0;

    // Mock status API and count requests
    await page.route(`**/api/status/${jobId}`, async route => {
      requestCount++;
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Wait for completion banner
    await expect(page.locator('text="✅ Completed!"')).toBeVisible();

    // Wait a bit to ensure no more polling requests
    await page.waitForTimeout(3000);

    // Should only have 1 request (initial load), no polling
    expect(requestCount).toBeLessThanOrEqual(2);
  });

  test('should display collection summary for completed job', async ({ page }) => {
    // Mock completed phase
    await page.route(`**/api/status/${jobId}`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          phase: 'completed',
          percent: 100,
          counts: { products: 5, videos: 8, images: 10, frames: 15 },
          collection: { products_done: true, videos_done: true },
          updated_at: new Date().toISOString(),
        },
      });
    });

    // Mock matching summary
    await page.route(`**/api/jobs/${jobId}/matching/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          matches_found: 12,
          pairs_processed: 40,
          evidence_ready: 12,
          avg_score: 0.85,
          p90_score: 0.92,
        },
      });
    });

    // Mock feature summary
    await page.route(`**/api/jobs/${jobId}/features/summary`, async route => {
      await route.fulfill({
        json: {
          job_id: jobId,
          product_images: {
            total: 10,
            segmented: 10,
            embedded: 10,
            keypoints: 10,
          },
          video_frames: {
            total: 15,
            segmented: 15,
            embedded: 15,
            keypoints: 15,
          },
        },
      });
    });

    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState('networkidle');

    // Assert collection summary is visible
    await expect(page.locator('text="Collection Summary"')).toBeVisible();
    await expect(page.locator('text="5"')).toBeVisible(); // products count
    await expect(page.locator('text="8"')).toBeVisible(); // videos count
  });
});
