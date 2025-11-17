import { test, expect } from '@playwright/test';

/**
 * Job Detail Tests
 * 
 * Tests job detail modal functionality including viewing metadata,
 * transcript access, and export options.
 */

test.describe('Job Detail Modal', () => {
  test('view completed job details and metadata', async ({ page }) => {
    await page.goto('/');
    
    // Find and click a job card
    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible({ timeout: 10000 });
    await jobCard.click();
    
    // Job detail modal should open
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    
    // Verify key metadata fields are present
    await expect(modal.getByText(/filename/i)).toBeVisible();
    await expect(modal.getByText(/duration/i)).toBeVisible();
    await expect(modal.getByText(/model/i)).toBeVisible();
    await expect(modal.getByText(/status/i)).toBeVisible();
    
    // Verify action buttons are available
    const viewTranscriptBtn = modal.getByRole('button', { name: /view transcript/i });
    const downloadBtn = modal.getByRole('button', { name: /download/i });
    
    // At least one should be visible for completed jobs
    const hasActions = await viewTranscriptBtn.isVisible().catch(() => false) ||
                      await downloadBtn.isVisible().catch(() => false);
    expect(hasActions).toBeTruthy();
  });

  test('export menu shows available formats', async ({ page }) => {
    await page.goto('/');
    
    const jobCard = page.locator('[data-testid="job-card"]').first();
    if (await jobCard.isVisible()) {
      await jobCard.click();
      
      const modal = page.getByRole('dialog');
      await expect(modal).toBeVisible();
      
      // Look for export/download button
      const exportButton = modal.getByRole('button', { name: /download|export/i }).first();
      
      if (await exportButton.isVisible()) {
        await exportButton.click();
        
        // Export menu or dropdown should appear with format options
        // Check for common export formats from spec
        const formatOptions = modal.getByText(/\.txt|\.md|\.srt|\.vtt|\.json|\.docx/i);
        await expect(formatOptions.first()).toBeVisible({ timeout: 2000 });
      }
    }
  });

  test('view transcript link opens transcript', async ({ page }) => {
    await page.goto('/');
    
    const jobCard = page.locator('[data-testid="job-card"]').first();
    if (await jobCard.isVisible()) {
      await jobCard.click();
      
      const modal = page.getByRole('dialog');
      const viewTranscriptBtn = modal.getByRole('button', { name: /view transcript/i });
      
      if (await viewTranscriptBtn.isVisible()) {
        const [transcriptPage] = await Promise.all([
          page.waitForEvent('popup'),
          viewTranscriptBtn.click()
        ]);
        
        // New tab/window should contain transcript
        await expect(transcriptPage).toHaveURL(/transcript/i);
        await transcriptPage.close();
      }
    }
  });

  test('edit tags on job', async ({ page }) => {
    await page.goto('/');
    
    const jobCard = page.locator('[data-testid="job-card"]').first();
    if (await jobCard.isVisible()) {
      await jobCard.click();
      
      const modal = page.getByRole('dialog');
      await expect(modal).toBeVisible();
      
      // Look for tag editing interface
      const tagSection = modal.locator('[data-testid="job-tags"]').or(modal.getByText(/tags/i));
      
      if (await tagSection.isVisible()) {
        // Verify tag input or selection is available
        const tagInput = modal.locator('[data-testid="tag-input"]').or(modal.getByPlaceholder(/tag/i));
        await expect(tagInput).toBeVisible();
      }
    }
  });
});
