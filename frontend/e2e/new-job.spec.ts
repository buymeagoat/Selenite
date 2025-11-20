import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';
// Use import.meta.url for path resolution under ESM.
import { fileURLToPath } from 'url';
import path from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const samplePath = path.join(__dirname, 'fixtures/media/sample.wav');

// NOTE: Backend createJob may be stubbed; this test only verifies UI interactions up to submit.

test.describe('New Job Modal', () => {
  test('user can submit a job via modal and see it on dashboard', async ({ page }) => {
    await uiLogin(page);
    // Navigate to dashboard if not already there (Navbar brand click)
    await page.getByRole('button', { name: 'Selenite' }).click();
    await expect(page.getByRole('heading', { name: 'Transcriptions' }).first()).toBeVisible();
    await expect(page.getByTestId('new-job-btn')).toBeVisible();
    await page.getByTestId('new-job-btn').click();
    await expect(page.getByTestId('new-job-modal-header')).toBeVisible();

    // Attach file via hidden input inside dropzone
    const dropzone = page.getByTestId('file-dropzone');
    await expect(dropzone).toBeVisible();
    const input = await dropzone.locator('input[type="file"]').elementHandle();
    await input?.setInputFiles(samplePath);

    // Model select change
    const modelSelect = page.getByTestId('model-select');
    await modelSelect.selectOption('tiny');
    await expect(modelSelect).toHaveValue('tiny');

    // Toggle timestamps off then back on
    const timestamps = page.getByTestId('timestamps-checkbox');
    await timestamps.click();
    await timestamps.click();

    // Start Transcription button enabled
    const startBtn = page.getByTestId('start-transcription-btn');
    await expect(startBtn).toBeEnabled();

    // Click submit to start transcription
    await startBtn.click();

    // Wait for success toast / dashboard refresh rather than modal disappearance
    const jobCard = page.locator('[data-testid="job-card"]');
    await expect(jobCard.first()).toBeVisible({ timeout: 20000 });
    // Optionally, check for job status or success message
    // await expect(page.getByText(/queued|processing|completed/i)).toBeVisible();
  });
});
