import { test, expect, type Page } from '@playwright/test';

/**
 * Job Detail Tests
 * 
 * Tests job detail modal functionality including viewing metadata,
 * transcript access, and export options.
 */

test.describe('Job Detail Modal', () => {
  const openCompletedJob = async (page: Page) => {
    const completedJob = page
      .locator('[data-testid="job-card"]')
      .filter({ hasText: /completed/i })
      .first();
    await expect(completedJob).toBeVisible({ timeout: 10000 });
    await completedJob.click();
    const modal = page.locator('[data-testid="job-detail-modal"]');
    await expect(modal).toBeVisible();
    return modal;
  };

  test('view completed job details and metadata', async ({ page }) => {
    await page.goto('/');
    
    const modal = await openCompletedJob(page);
    
    // Verify key metadata fields are present
    const metadata = modal.locator('[data-testid="job-metadata"]');
    await expect(metadata).toBeVisible();
    await expect(metadata.getByText(/^duration$/i)).toBeVisible();
    await expect(metadata.getByText(/model/i)).toBeVisible();
    await expect(metadata.getByText(/language/i)).toBeVisible();
    await expect(metadata.getByText(/file size/i)).toBeVisible();
    // Status badge near the header should reflect completed state
    await expect(modal.getByText(/completed/i)).toBeVisible();
    
    // Verify action buttons are available
    const viewTranscriptBtn = modal.getByRole('button', { name: /view transcript/i });
    const downloadBtn = modal.getByRole('button', { name: /download transcript/i });
    await expect(viewTranscriptBtn).toBeVisible();
    await expect(downloadBtn).toBeVisible();
  });

  test('export menu shows available formats', async ({ page }) => {
    await page.goto('/');
    
    const modal = await openCompletedJob(page);
    
    // Look for export/download button
    const exportButton = modal.getByRole('button', { name: /download transcript/i });
    await expect(exportButton).toBeVisible();
    await exportButton.click();
    
    // Export menu or dropdown should appear with format options
    const formatOptions = modal.locator('[data-testid="download-options"] button');
    await expect(formatOptions.first()).toBeVisible({ timeout: 2000 });
    await expect(formatOptions.first()).toContainText(/\.(txt|md|srt|vtt|json|docx)/i);
  });

  test('view transcript link opens transcript', async ({ page }) => {
    await page.goto('/');
    
    const modal = await openCompletedJob(page);
    
    const viewTranscriptBtn = modal.getByRole('button', { name: /view transcript/i });
    await expect(viewTranscriptBtn).toBeVisible();
    const [transcriptPage] = await Promise.all([
      page.waitForEvent('popup'),
      viewTranscriptBtn.click()
    ]);
    
    // New tab/window should contain transcript
    await expect(transcriptPage).toHaveURL(/transcript/i);
    await transcriptPage.close();
  });

  test('edit tags on job', async ({ page }) => {
    await page.goto('/');
    
    const modal = await openCompletedJob(page);
    
    const tagSection = modal.locator('[data-testid="job-tags"]');
    await expect(tagSection).toBeVisible();
    const tagInput = modal.locator('[data-testid="tag-input"]');
    await expect(tagInput).toBeVisible();
  });
});
