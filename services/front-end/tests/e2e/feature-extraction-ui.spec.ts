import { test, expect } from '@playwright/test';

test.describe('Feature Extraction UI', () => {
  test('should display feature extraction banner when phase is feature_extraction', async ({ page }) => {
    // Log all requests to debug
    page.on('request', request => {
      if (request.url().includes('api')) {
        console.log('Request:', request.url());
      }
    });

    // Set up all route mocks BEFORE navigation
    await page.route('**/api/jobs/test-job-123/status', async (route) => {
      console.log('Mocking status endpoint');

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          phase: 'feature_extraction',
          percent: 65,
          counts: {
            products: 10,
            videos: 5,
            images: 25,
            frames: 150
          },
          collection: {
            products_done: true,
            videos_done: true
          },
          updated_at: new Date().toISOString()
        })
      });
    });

    await page.route('**/api/jobs/test-job-123/features/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          product_images: {
            total: 25,
            segment: { done: 20, percent: 80 },
            embedding: { done: 15, percent: 60 },
            keypoints: { done: 10, percent: 40 }
          },
          video_frames: {
            total: 150,
            segment: { done: 120, percent: 80 },
            embedding: { done: 90, percent: 60 },
            keypoints: { done: 60, percent: 40 }
          },
          updated_at: new Date().toISOString()
        })
      });
    });

    await page.route('**/api/jobs/test-job-123', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          query: 'ergonomic pillows',
          created_at: new Date().toISOString()
        })
      });
    });

    await page.route('**/api/jobs/test-job-123/products*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          limit: 10,
          offset: 0
        })
      });
    });

    await page.route('**/api/jobs/test-job-123/videos*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          limit: 10,
          offset: 0
        })
      });
    });

    // Navigate to job detail page
    await page.goto('/en/jobs/test-job-123');

    // Wait for the page to load
    await page.waitForLoadState('domcontentloaded');

    // Check for feature extraction banner
    await expect(page.getByText('Feature extraction in progress')).toBeVisible({ timeout: 10000 });
    
    // Check banner content
    await expect(page.getByText('10 products')).toBeVisible();
    await expect(page.getByText('5 videos')).toBeVisible();
    await expect(page.getByText('25 images')).toBeVisible();
    await expect(page.getByText('150 frames')).toBeVisible();
    await expect(page.getByText('65%')).toBeVisible();

    // Check for feature extraction panel
    await expect(page.getByRole('heading', { name: 'Product Images' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Video Frames' })).toBeVisible();

    // Check for progress steps
    await expect(page.getByText('Segmentation')).toBeVisible();
    await expect(page.getByText('Embedding')).toBeVisible();
    await expect(page.getByText('Keypoints')).toBeVisible();

    // Check for progress fractions
    await expect(page.getByText('20/25')).toBeVisible();
    await expect(page.getByText('15/25')).toBeVisible();
    await expect(page.getByText('10/25')).toBeVisible();
  });

  test.skip('should display feature toolbar in panels during feature extraction', async ({ page }) => {
    // This test is skipped because panel toolbars are not yet implemented
    // TODO: Implement panel toolbars as per spec section 5.3
  });

  test('should not display feature extraction UI when phase is collection', async ({ page }) => {
    // Mock the API responses for collection phase
    await page.route('**/api/jobs/test-job-123/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          phase: 'collection',
          percent: 20,
          counts: {
            products: 5,
            videos: 3,
            images: 0,
            frames: 0
          },
          collection: {
            products_done: false,
            videos_done: false
          },
          updated_at: new Date().toISOString()
        })
      });
    });

    await page.route('**/api/jobs/test-job-123', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          query: 'ergonomic pillows',
          created_at: new Date().toISOString()
        })
      });
    });

    await page.route('**/api/jobs/test-job-123/products*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          limit: 10,
          offset: 0
        })
      });
    });

    await page.route('**/api/jobs/test-job-123/videos*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          limit: 10,
          offset: 0
        })
      });
    });

    // Navigate to job detail page
    await page.goto('/en/jobs/test-job-123');

    // Wait for the page to load
    await page.waitForLoadState('domcontentloaded');

    // Feature extraction banner should NOT be visible
    await expect(page.getByText('Feature extraction in progress')).not.toBeVisible({ timeout: 5000 });
    
    // Feature extraction panel should NOT be visible
    await expect(page.getByRole('heading', { name: 'Product Images' })).not.toBeVisible();
  });
});
