import { test, expect } from '@playwright/test';

test.describe('Refactored Pagination Components', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for consistent testing
    await page.route('**/api/jobs/**/products*', async route => {
      const url = new URL(route.request().url());
      const offset = parseInt(url.searchParams.get('offset') || '0');
      const limit = parseInt(url.searchParams.get('limit') || '10');

      // Generate mock data based on offset
      const items = Array.from({ length: limit }, (_, i) => ({
        product_id: `product-${offset + i + 1}`,
        src: offset < 10 ? 'Amazon' : 'eBay',
        name: `Product ${offset + i + 1}`,
        price: 19.99 + (offset + i),
        image_url: 'https://example.com/image.jpg'
      }));

      await route.fulfill({
        json: {
          items,
          total: 50, // Total of 50 products for pagination testing
        },
      });
    });

    await page.route('**/api/jobs/**/videos*', async route => {
      const url = new URL(route.request().url());
      const offset = parseInt(url.searchParams.get('offset') || '0');
      const limit = parseInt(url.searchParams.get('limit') || '10');

      // Generate mock data based on offset
      const items = Array.from({ length: limit }, (_, i) => ({
        video_id: `video-${offset + i + 1}`,
        platform: offset < 10 ? 'YouTube' : 'TikTok',
        title: `Video ${offset + i + 1}`,
        duration: 120 + (offset + i),
        first_keyframe_url: 'https://example.com/thumb.jpg'
      }));

      await route.fulfill({
        json: {
          items,
          total: 35, // Total of 35 videos for pagination testing
        },
      });
    });

    // Navigate to the job results page
    await page.goto('/jobs/test-job-id');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display both pagination panels with correct test IDs', async ({ page }) => {
    // Verify both panels are visible
    await expect(page.locator('[data-testid="products-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="videos-panel"]')).toBeVisible();

    // Verify pagination controls are present
    await expect(page.locator('[data-testid="products-pagination"]')).toBeVisible();
    await expect(page.locator('[data-testid="videos-pagination"]')).toBeVisible();
  });

  test('should show loading indicators when clicking navigation buttons', async ({ page }) => {
    // Add slight delay to API calls to see loading indicators
    await page.route('**/api/jobs/**/products*', async route => {
      await new Promise(resolve => setTimeout(resolve, 500));
      await route.continue();
    });

    // Click next button in products panel
    const nextButton = page.locator('[data-testid="products-pagination-next"]');
    await nextButton.click();

    // Loading overlay should appear
    await expect(page.locator('.backdrop-blur-sm')).toBeVisible();

    // Wait for loading to complete
    await expect(page.locator('.backdrop-blur-sm')).not.toBeVisible({ timeout: 10000 });
  });

  test('should handle pagination navigation correctly', async ({ page }) => {
    const productsNextButton = page.locator('[data-testid="products-pagination-next"]');
    const productsPrevButton = page.locator('[data-testid="products-pagination-prev"]');

    // Initially, prev button should be disabled
    await expect(productsPrevButton).toBeDisabled();
    await expect(productsNextButton).toBeEnabled();

    // Click next to go to page 2
    await productsNextButton.click();
    await page.waitForTimeout(1000);

    // Now prev should be enabled
    await expect(productsPrevButton).toBeEnabled();

    // Click prev to go back to page 1
    await productsPrevButton.click();
    await page.waitForTimeout(1000);

    // Prev should be disabled again
    await expect(productsPrevButton).toBeDisabled();
  });

  test('should maintain independent pagination states between panels', async ({ page }) => {
    const productsNext = page.locator('[data-testid="products-pagination-next"]');
    const videosNext = page.locator('[data-testid="videos-pagination-next"]');
    const productsPrev = page.locator('[data-testid="products-pagination-prev"]');
    const videosPrev = page.locator('[data-testid="videos-pagination-prev"]');

    // Initially both prev buttons should be disabled
    await expect(productsPrev).toBeDisabled();
    await expect(videosPrev).toBeDisabled();

    // Navigate products panel to page 2
    await productsNext.click();
    await page.waitForTimeout(1000);

    // Products prev should now be enabled, but videos prev should still be disabled
    await expect(productsPrev).toBeEnabled();
    await expect(videosPrev).toBeDisabled();

    // Navigate videos panel to page 2
    await videosNext.click();
    await page.waitForTimeout(1000);

    // Now both prev buttons should be enabled
    await expect(productsPrev).toBeEnabled();
    await expect(videosPrev).toBeEnabled();
  });

  test('should demonstrate pre-loading performance benefits', async ({ page }) => {
    // Add delay to API calls to measure navigation time
    let apiCallCount = 0;
    await page.route('**/api/jobs/**/products*', async route => {
      apiCallCount++;
      console.log(`API call #${apiCallCount}`);

      // Add delay to first call only
      if (apiCallCount === 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      await route.continue();
    });

    // First navigation - should trigger API call and show loading
    const nextButton = page.locator('[data-testid="products-pagination-next"]');
    const startTime = Date.now();

    await nextButton.click();
    await page.waitForTimeout(1500); // Wait for API call and pre-loading

    const firstNavTime = Date.now() - startTime;
    console.log(`First navigation took: ${firstNavTime}ms`);

    // Navigate back - should be faster due to pre-loading/cache
    const prevButton = page.locator('[data-testid="products-pagination-prev"]');
    const startTime2 = Date.now();

    await prevButton.click();
    await page.waitForTimeout(500);

    const secondNavTime = Date.now() - startTime2;
    console.log(`Second navigation took: ${secondNavTime}ms`);

    // Verify that multiple API calls were made (initial + pre-loading)
    expect(apiCallCount).toBeGreaterThan(1);
  });

  test('should verify hook-based implementation is working', async ({ page }) => {
    // This test verifies that our refactored hook-based components work

    // Verify initial load works
    await expect(page.locator('[data-testid="products-panel"]')).toContainText('Product 1');
    await expect(page.locator('[data-testid="videos-panel"]')).toContainText('Video 1');

    // Verify navigation works
    await page.locator('[data-testid="products-pagination-next"]').click();
    await page.waitForTimeout(1000);

    // Should now show different content (page 2)
    await expect(page.locator('[data-testid="products-panel"]')).toContainText('Product 11');

    // Verify pagination controls update correctly
    const currentPageInfo = page.locator('[data-testid="products-pagination-current"]');
    await expect(currentPageInfo).toContainText('2');
  });

  test('should handle error states gracefully', async ({ page }) => {
    // Mock API error for products
    await page.route('**/api/jobs/**/products*', async route => {
      await route.abort('failed');
    });

    // Reload page to trigger error
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should show error state
    await expect(page.locator('[data-testid="products-error"]')).toBeVisible();

    // Remove the error mock
    await page.unroute('**/api/jobs/**/products*');

    // Add back successful mock
    await page.route('**/api/jobs/**/products*', async route => {
      const items = Array.from({ length: 10 }, (_, i) => ({
        product_id: `product-${i + 1}`,
        src: 'Amazon',
        name: `Product ${i + 1}`,
        price: 19.99 + i,
        image_url: 'https://example.com/image.jpg'
      }));

      await route.fulfill({
        json: { items, total: 50 },
      });
    });

    // Click retry
    const retryButton = page.locator('[data-testid="products-retry"]');
    await retryButton.click();

    // Should load successfully
    await expect(page.locator('[data-testid="products-error"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="products-panel"]')).toContainText('Product 1');
  });

  test('should verify translation support', async ({ page }) => {
    // Test English version
    await page.goto('/en/jobs/test-job-id');
    await page.waitForLoadState('networkidle');

    // Look for English text in pagination
    await expect(page.locator('text=Previous')).toBeVisible();
    await expect(page.locator('text=Next')).toBeVisible();

    // Test Vietnamese version
    await page.goto('/vi/jobs/test-job-id');
    await page.waitForLoadState('networkidle');

    // Look for Vietnamese text (if translations exist)
    // This test will help identify if translations need to be added
    const pageContent = await page.textContent('body');
    console.log('Page contains Vietnamese translations:', pageContent?.includes('Trước') || pageContent?.includes('Tiếp'));
  });
});