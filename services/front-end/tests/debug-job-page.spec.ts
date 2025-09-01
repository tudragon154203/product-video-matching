import { test, expect } from '@playwright/test';

test.describe('Debug Job Page Issues', () => {
  test('Navigate to Vietnamese job page and identify bugs', async ({ page }) => {
    // Enable console logging to capture errors
    page.on('console', msg => {
      console.log(`Console ${msg.type()}: ${msg.text()}`);
    });

    // Capture network errors
    page.on('requestfailed', request => {
      console.log(`Request failed: ${request.url()} - ${request.failure()?.errorText}`);
    });

    // Navigate to the job page
    await page.goto('http://localhost:3000/vi/jobs/278631ef-f1ef-428c-9596-026cb933bced');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Take a screenshot for debugging
    await page.screenshot({ 
      path: 'tests/debug-job-page-screenshot.png', 
      fullPage: true 
    });

    // Check for common error indicators
    const errorElements = await page.locator('[data-testid*="error"]').count();
    console.log(`Found ${errorElements} error elements`);

    // Check for loading states that might be stuck
    const loadingElements = await page.locator('[data-testid*="loading"]').count();
    console.log(`Found ${loadingElements} loading elements`);

    // Check if images are failing to load
    const images = await page.locator('img').all();
    for (const img of images) {
      const src = await img.getAttribute('src');
      const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
      if (naturalWidth === 0 && src) {
        console.log(`Failed to load image: ${src}`);
      }
    }

    // Check for Next.js image errors specifically
    const nextImages = await page.locator('img[src*="localhost:8888"]').all();
    console.log(`Found ${nextImages.length} images from localhost:8888`);

    // Wait a bit to see if any async errors occur
    await page.waitForTimeout(3000);

    // Check page title and basic content
    const title = await page.title();
    console.log(`Page title: ${title}`);

    // Check if the job ID is displayed correctly
    const jobIdElement = await page.locator('text=278631ef-f1ef-428c-9596-026cb933bced').first();
    if (await jobIdElement.isVisible()) {
      console.log('Job ID is visible on page');
    } else {
      console.log('Job ID is NOT visible on page');
    }

    // Check for Vietnamese text to ensure localization is working
    const vietnameseText = await page.locator('text=/Sản phẩm|Video|Kết quả/').count();
    console.log(`Found ${vietnameseText} Vietnamese text elements`);
  });
});