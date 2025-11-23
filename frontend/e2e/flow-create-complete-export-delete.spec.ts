import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';
import path from 'path';
import fs from 'fs';

const SAMPLE_FILE = path.join(__dirname, 'fixtures', 'sample.mp3');

test.describe('Create → Complete → Export → Delete flow', () => {
  test.beforeEach(async ({ page }) => {
    await uiLogin(page);
  });

  test('desktop flow', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Start a new job
    await page.getByRole('button', { name: /new job/i }).click();
    const fileInput = page.getByLabel(/Audio\/Video File/i);
    await fileInput.setInputFiles(SAMPLE_FILE);
    await page.getByRole('button', { name: /Start Transcription/i }).click();

    // Wait for job card to show completed
    const jobCard = page.getByTestId('job-card').first();
    await expect(jobCard.getByText(/Completed/i)).toBeVisible({ timeout: 90_000 });

    // Download transcript TXT
    const downloadBtn = jobCard.getByRole('button', { name: /Download/i }).first();
    await downloadBtn.click();

    // Open transcript view and verify
    const viewBtn = jobCard.getByRole('button', { name: /View/i });
    await viewBtn.click();
    await expect(page.getByText(/Transcript/)).toBeVisible();
    await page.getByRole('button', { name: /Download TXT/i }).click();

    // Delete job
    await page.goto('/', { waitUntil: 'networkidle' });
    await jobCard.getByRole('button', { name: /Delete/i }).click();
    await page.getByRole('button', { name: /Confirm/i }).click();
    await expect(jobCard).toBeHidden({ timeout: 10_000 });
  });

  test('mobile flow', async ({ page, browser }) => {
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await uiLogin(mobile);
    await mobile.goto('/', { waitUntil: 'networkidle' });

    // Start a new job
    await mobile.getByRole('button', { name: /new job/i }).click();
    const fileInput = mobile.getByLabel(/Audio\/Video File/i);
    await fileInput.setInputFiles(SAMPLE_FILE);
    await mobile.getByRole('button', { name: /Start Transcription/i }).click();

    // Wait for job to complete
    const jobCard = mobile.getByTestId('job-card').first();
    await expect(jobCard.getByText(/Completed/i)).toBeVisible({ timeout: 90_000 });

    // Delete job to clean up
    await mobile.goto('/', { waitUntil: 'networkidle' });
    await jobCard.getByRole('button', { name: /Delete/i }).click();
    await mobile.getByRole('button', { name: /Confirm/i }).click();
    await expect(jobCard).toBeHidden({ timeout: 10_000 });
    await mobile.close();
  });
});
