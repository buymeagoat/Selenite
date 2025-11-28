import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SAMPLE_FILE = path.resolve(process.cwd(), 'e2e', 'fixtures', 'media', 'sample.wav');

test.describe('Create → Complete → Export → Delete flow', () => {
  test.beforeEach(async ({ page }) => {
    await uiLogin(page);
  });

  test('desktop flow', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Start a new job
    await page.getByRole('button', { name: /new job/i }).click();
    const fileInput = page.getByTestId('file-input');
    await fileInput.setInputFiles(SAMPLE_FILE);
    await page.getByRole('button', { name: /Start Transcription/i }).click();

    // Wait for this job to show completed
    const jobCard = page.getByTestId('job-card').filter({ hasText: 'sample.wav' }).first();
    await expect(jobCard.getByText(/Completed/i)).toBeVisible({ timeout: 90_000 });

    // Download transcript TXT
    const downloadPromise = page.waitForEvent('download');
    await jobCard.getByRole('button', { name: /Download/i }).first().click();
    await downloadPromise;

    // Open transcript view and verify
    const [popup] = await Promise.all([
      page.waitForEvent('popup'),
      jobCard.getByRole('button', { name: /View/i }).click()
    ]);
    await popup.waitForLoadState('domcontentloaded');
    await expect(popup.getByRole('heading', { name: /transcript/i })).toBeVisible();
    await popup.getByRole('button', { name: /Download TXT/i }).click();
    await popup.close();

    // Delete job
    await jobCard.click();
    const detailModal = page.getByRole('dialog');
    await expect(detailModal).toBeVisible();
    await detailModal.getByRole('button', { name: /delete job/i }).click();
    const confirmDialog = page.getByRole('dialog', { name: /delete job/i });
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.getByRole('button', { name: /^delete$/i }).click();
    await expect(detailModal).toBeHidden({ timeout: 10_000 });
  });

  test('mobile flow', async ({ page, browser }) => {
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await uiLogin(mobile);
    await mobile.goto('/', { waitUntil: 'networkidle' });

    // Start a new job
    await mobile.getByRole('button', { name: /new job/i }).click();
    const fileInput = mobile.getByTestId('file-input');
    await fileInput.setInputFiles(SAMPLE_FILE);
    await mobile.getByRole('button', { name: /Start Transcription/i }).click();

    // Wait for job to complete
    const jobCard = mobile.getByTestId('job-card').filter({ hasText: 'sample.wav' }).first();
    await expect(jobCard.getByText(/Completed/i)).toBeVisible({ timeout: 90_000 });

    // Delete job to clean up via detail modal
    await jobCard.click();
    const detailModal = mobile.getByRole('dialog');
    await expect(detailModal).toBeVisible();
    await detailModal.getByRole('button', { name: /delete job/i }).click();
    const confirmDialog = mobile.getByRole('dialog', { name: /delete job/i });
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.getByRole('button', { name: /^delete$/i }).click();
    await expect(detailModal).toBeHidden({ timeout: 10_000 });
    await mobile.close();
  });
});
