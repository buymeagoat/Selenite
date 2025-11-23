import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';
import { runAxe } from './axe.config';

test.describe('Accessibility smokes', () => {
  test.beforeEach(async ({ page }) => {
    await uiLogin(page);
  });

  test('Dashboard has no critical axe violations', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const violations = await runAxe(page, 'Dashboard');
    expect(violations.length).toBe(0);
  });

  test('Transcript view has no critical axe violations', async ({ page }) => {
    // Navigate to transcripts list and open first one if it exists, otherwise skip gracefully
    await page.goto('/', { waitUntil: 'networkidle' });
    const transcriptLinks = page.getByRole('link', { name: /transcript/i });
    const count = await transcriptLinks.count();
    if (count === 0) {
      test.skip(true, 'No transcripts available to test accessibility.');
    }
    await transcriptLinks.nth(0).click();
    await page.waitForLoadState('networkidle');
    const violations = await runAxe(page, 'TranscriptView');
    expect(violations.length).toBe(0);
  });
});
