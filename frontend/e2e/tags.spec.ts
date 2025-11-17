import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';

// Tags UI smoke: with current stub data, verifies tag-related components appear after login.
// Adjust selectors when Tag Management page is implemented.

test.describe('Tags UI Smoke', () => {
  test('tag input appears inside New Job modal (placeholder)', async ({ page }) => {
    await uiLogin(page);
    await page.getByRole('button', { name: 'Selenite' }).click();
    await expect(page.getByRole('heading', { name: 'Transcriptions' })).toBeVisible();
    await expect(page.getByTestId('new-job-btn')).toBeVisible();
    await page.getByTestId('new-job-btn').click();
    // Currently no dedicated tag input in NewJobModal; this test documents absence.
    const maybeTagInput = page.getByTestId('tag-input').first();
    // Expect it not to be found yet; will be updated when feature arrives.
    await expect(maybeTagInput).not.toBeVisible();
  });
});
