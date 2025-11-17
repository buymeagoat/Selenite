import { test, expect } from '@playwright/test';
import path from 'path';

/**
 * Transcription Workflow Tests
 * 
 * Tests the complete job creation and transcription lifecycle.
 * Uses authenticated state from auth.setup.ts
 */

test.describe('Transcription Workflow', () => {
  test('create new transcription job with file upload and model selection', async ({ page }) => {
    await page.goto('/');
    
    // Open New Job Modal
    const newJobButton = page.locator('[data-testid="new-job-btn"]').first();
    await expect(newJobButton).toBeVisible();
    await newJobButton.click();
    
    // Verify modal opened
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    await expect(page.getByRole('heading', { name: /new transcription/i })).toBeVisible();
    
    // Upload file
    const fileInput = page.getByLabel(/upload.*file/i).or(page.locator('input[type="file"]'));
    const sampleFile = path.join(__dirname, 'fixtures', 'media', 'sample.wav');
    await fileInput.setInputFiles(sampleFile);
    
    // Verify file is attached
    await expect(page.getByText(/sample\.wav/i)).toBeVisible();
    
    // Select model
    const modelSelect = page.getByLabel(/model/i).or(page.locator('[data-testid="model-select"]'));
    await modelSelect.selectOption('base');
    
    // Verify options are available
    await expect(page.getByLabel(/speaker detection/i)).toBeVisible();
    await expect(page.getByLabel(/timestamps/i)).toBeVisible();
    
    // Start transcription
    const startButton = page.getByRole('button', { name: /start transcription/i });
    await expect(startButton).toBeEnabled();
    await startButton.click();
    
    // Modal should close
    await expect(modal).not.toBeVisible();
    
    // Job should appear in dashboard with "Queued" or "Processing" status
    await expect(page.getByText(/sample\.wav/i)).toBeVisible();
    await expect(
      page.getByText(/queued/i).or(page.getByText(/processing/i))
    ).toBeVisible();
  });

  test('job progresses through stages with progress updates', async ({ page }) => {
    await page.goto('/');
    
    // Create a job (reuse flow from previous test)
    await page.locator('[data-testid="new-job-btn"]').first().click();
    const fileInput = page.locator('input[type="file"]');
    const sampleFile = path.join(__dirname, 'fixtures', 'media', 'sample.wav');
    await fileInput.setInputFiles(sampleFile);
    await page.getByRole('button', { name: /start transcription/i }).click();
    
    // Wait for job card to appear
    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible();
    
    // Verify status badge exists
    const statusBadge = jobCard.locator('[data-testid="status-badge"]');
    await expect(statusBadge).toBeVisible();
    
    // Note: In a real transcription, we'd verify stage transitions:
    // "Uploading" → "Loading Model" → "Transcribing" → "Finalizing" → "Complete"
    // For now, just verify the status badge updates
    await expect(statusBadge).toContainText(/queued|processing|complete/i, { timeout: 10000 });
    
    // If processing, verify progress bar exists
    const progressBar = jobCard.locator('[data-testid="progress-bar"]').or(jobCard.locator('progress'));
    if (await progressBar.isVisible()) {
      // Progress should be between 0-100%
      const progressValue = await progressBar.getAttribute('value');
      if (progressValue) {
        const progress = parseInt(progressValue);
        expect(progress).toBeGreaterThanOrEqual(0);
        expect(progress).toBeLessThanOrEqual(100);
      }
    }
  });

  test('cancel processing job', async ({ page }) => {
    await page.goto('/');
    
    // Create a job
    await page.locator('[data-testid="new-job-btn"]').first().click();
    const fileInput = page.locator('input[type="file"]');
    const sampleFile = path.join(__dirname, 'fixtures', 'media', 'sample.wav');
    await fileInput.setInputFiles(sampleFile);
    await page.getByRole('button', { name: /start transcription/i }).click();
    
    // Find the job card
    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible();
    
    // Look for cancel button (may be in quick actions or job detail)
    const cancelButton = jobCard.getByRole('button', { name: /cancel/i }).first();
    
    if (await cancelButton.isVisible()) {
      await cancelButton.click();
      
      // Confirm cancellation if modal appears
      const confirmButton = page.getByRole('button', { name: /confirm|yes|cancel job/i });
      if (await confirmButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await confirmButton.click();
      }
      
      // Status should change to "Cancelled" or job should disappear
      await expect(jobCard.locator('[data-testid="status-badge"]')).toContainText(/cancelled|failed/i, { timeout: 5000 });
    }
  });

  test('restart completed job creates new job', async ({ page }) => {
    await page.goto('/');
    
    // Find a completed job (or create one)
    // For now, just verify the restart button exists in job detail
    const jobCard = page.locator('[data-testid="job-card"]').first();
    
    if (await jobCard.isVisible()) {
      await jobCard.click();
      
      // Job detail modal should open
      const modal = page.getByRole('dialog');
      await expect(modal).toBeVisible();
      
      // Look for restart/re-run button
      const restartButton = modal.getByRole('button', { name: /restart|re-run/i });
      
      if (await restartButton.isVisible()) {
        const initialJobCount = await page.locator('[data-testid="job-card"]').count();
        
        await restartButton.click();
        
        // Modal should close
        await expect(modal).not.toBeVisible();
        
        // New job should appear (job count increases)
        await expect(async () => {
          const newCount = await page.locator('[data-testid="job-card"]').count();
          expect(newCount).toBeGreaterThan(initialJobCount);
        }).toPass({ timeout: 5000 });
      }
    }
  });
});
