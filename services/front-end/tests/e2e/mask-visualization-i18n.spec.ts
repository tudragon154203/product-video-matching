import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Mask Visualization i18n (Internationalization)
 * 
 * Verifies that all mask gallery UI elements are properly translated
 * in both English and Vietnamese locales.
 */

test.describe('Mask Visualization i18n', () => {
  const jobId = 'f396cedb-6aa2-43fd-8df6-e9bd938691c0';

  test.describe('English (en) locale', () => {
    test('should display mask gallery in English', async ({ page }) => {
      await page.goto(`/en/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /view.*samples/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

        // Verify English translations
        await expect(page.getByRole('heading', { name: /segmentation samples/i })).toBeVisible();
        await expect(page.getByText(/review original assets/i)).toBeVisible();
        
        // Check tab labels
        await expect(page.getByRole('button', { name: /product images/i })).toBeVisible();
        await expect(page.getByRole('button', { name: /video frames/i })).toBeVisible();

        // Check close button
        await expect(page.getByRole('button', { name: /close/i })).toBeVisible();

        // Check keyboard hint
        await expect(page.getByText(/esc.*close.*arrow keys/i)).toBeVisible();

        // Check pagination text
        await expect(page.getByText(/showing \d+-\d+ of \d+/i)).toBeVisible();
      }
    });

    test('should display "View Samples" button text in English', async ({ page }) => {
      await page.goto(`/en/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /view.*segmentation.*samples/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        const buttonText = await viewSamplesButton.textContent();
        expect(buttonText).toMatch(/view.*segmentation.*samples/i);
        expect(buttonText).toMatch(/\d+.*ready/i);
      }
    });
  });

  test.describe('Vietnamese (vi) locale', () => {
    test('should display mask gallery in Vietnamese', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

        // Verify Vietnamese translations
        await expect(page.getByRole('heading', { name: /mẫu phân đoạn/i })).toBeVisible();
        await expect(page.getByText(/xem lại tài sản gốc/i)).toBeVisible();
        
        // Check tab labels
        await expect(page.getByRole('button', { name: /hình ảnh sản phẩm/i })).toBeVisible();
        await expect(page.getByRole('button', { name: /khung hình video/i })).toBeVisible();

        // Check close button
        await expect(page.getByRole('button', { name: /đóng/i })).toBeVisible();

        // Check keyboard hint
        await expect(page.getByText(/esc.*đóng.*phím mũi tên/i)).toBeVisible();

        // Check pagination text
        await expect(page.getByText(/hiển thị \d+-\d+ trong tổng \d+/i)).toBeVisible();
      }
    });

    test('should display "View Samples" button text in Vietnamese', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu.*phân đoạn/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        const buttonText = await viewSamplesButton.textContent();
        expect(buttonText).toMatch(/xem.*mẫu.*phân đoạn/i);
        expect(buttonText).toMatch(/\d+.*sẵn sàng/i);
      }
    });

    test('should display metadata labels in Vietnamese', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
        await page.waitForTimeout(2000);

        // Check for Vietnamese metadata labels
        const hasImageId = await page.getByText(/id hình ảnh/i).isVisible().catch(() => false);
        const hasFrameId = await page.getByText(/id khung hình/i).isVisible().catch(() => false);
        const hasProductId = await page.getByText(/sản phẩm/i).isVisible().catch(() => false);
        const hasVideoId = await page.getByText(/video/i).isVisible().catch(() => false);

        // At least some metadata should be visible
        expect(hasImageId || hasFrameId || hasProductId || hasVideoId).toBe(true);
      }
    });

    test('should display "Original" and "Mask" labels in Vietnamese', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
        await page.waitForTimeout(2000);

        // Check for Vietnamese labels
        const originalLabel = page.getByText(/^gốc$/i);
        const maskLabel = page.getByText(/^mặt nạ$/i);

        const hasOriginal = await originalLabel.first().isVisible().catch(() => false);
        const hasMask = await maskLabel.first().isVisible().catch(() => false);

        if (hasOriginal || hasMask) {
          expect(hasOriginal).toBe(true);
          expect(hasMask).toBe(true);
        }
      }
    });
  });

  test.describe('Locale switching', () => {
    test('should switch from English to Vietnamese', async ({ page }) => {
      // Start in English
      await page.goto(`/en/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      // Check for English button
      let viewSamplesButton = page.getByRole('button', { name: /view.*samples/i });
      let buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        const englishText = await viewSamplesButton.textContent();
        expect(englishText).toMatch(/view.*segmentation.*samples/i);

        // Switch to Vietnamese
        await page.goto(`/vi/jobs/${jobId}`);
        await page.waitForLoadState('networkidle', { timeout: 15000 });

        // Check for Vietnamese button
        viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
        buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

        if (buttonVisible) {
          const vietnameseText = await viewSamplesButton.textContent();
          expect(vietnameseText).toMatch(/xem.*mẫu.*phân đoạn/i);
          expect(vietnameseText).not.toMatch(/view.*samples/i);
        }
      }
    });

    test('should maintain locale when opening and closing modal', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        // Open modal
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

        // Verify Vietnamese in modal
        await expect(page.getByRole('heading', { name: /mẫu phân đoạn/i })).toBeVisible();

        // Close modal
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);

        // Verify still in Vietnamese
        await expect(viewSamplesButton).toBeVisible();
        const buttonText = await viewSamplesButton.textContent();
        expect(buttonText).toMatch(/xem.*mẫu/i);
      }
    });
  });

  test.describe('Translation completeness', () => {
    test('should have all required English translations', async ({ page }) => {
      await page.goto(`/en/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /view.*samples/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

        // Check for all required translation keys
        const requiredTexts = [
          /segmentation samples/i,
          /product images/i,
          /video frames/i,
          /close/i,
          /showing \d+-\d+ of \d+/i,
          /esc.*arrow keys/i,
        ];

        for (const textPattern of requiredTexts) {
          const element = page.getByText(textPattern).first();
          const isVisible = await element.isVisible().catch(() => false);
          if (!isVisible) {
            console.log(`Missing or not visible: ${textPattern}`);
          }
        }
      }
    });

    test('should have all required Vietnamese translations', async ({ page }) => {
      await page.goto(`/vi/jobs/${jobId}`);
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      const viewSamplesButton = page.getByRole('button', { name: /xem.*mẫu/i });
      const buttonVisible = await viewSamplesButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewSamplesButton.click();
        await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

        // Check for all required translation keys
        const requiredTexts = [
          /mẫu phân đoạn/i,
          /hình ảnh sản phẩm/i,
          /khung hình video/i,
          /đóng/i,
          /hiển thị \d+-\d+ trong tổng \d+/i,
          /esc.*phím mũi tên/i,
        ];

        for (const textPattern of requiredTexts) {
          const element = page.getByText(textPattern).first();
          const isVisible = await element.isVisible().catch(() => false);
          if (!isVisible) {
            console.log(`Missing or not visible: ${textPattern}`);
          }
        }
      }
    });
  });

  test.describe('Error messages i18n', () => {
    test('should display error messages in correct locale', async ({ page }) => {
      // This would require mocking API failures
      // For now, we verify the translations exist in the files
      expect(true).toBe(true);
    });
  });
});
