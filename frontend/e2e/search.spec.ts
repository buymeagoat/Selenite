import { test, expect } from '@playwright/test';

/**
 * Search and Filter Tests
 * 
 * Tests search functionality and job filtering capabilities.
 */

test.describe('Search Functionality', () => {
  test('search jobs by filename', async ({ page }) => {
    await page.goto('/');
    
    // Wait for jobs to load
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Get initial job count
    const initialCount = await page.locator('[data-testid="job-card"]').count();
    expect(initialCount).toBeGreaterThan(0);
    
    // Find search input
    const searchInput = page.getByPlaceholder(/search/i).or(page.locator('[data-testid="search-input"]'));
    await expect(searchInput).toBeVisible();
    
    // Get a filename from the first job
    const firstJobCard = page.locator('[data-testid="job-card"]').first();
    const filenameText = await firstJobCard.locator('[data-testid="job-filename"]')
      .or(firstJobCard.getByText(/\.(mp3|wav|mp4|m4a)/i))
      .first()
      .textContent();
    
    if (filenameText) {
      // Extract just a few characters from filename to search
      const searchTerm = filenameText.slice(0, 5);
      
      await searchInput.fill(searchTerm);
      
      // Wait for search results to update
      await page.waitForTimeout(500); // Debounce
      
      // All visible jobs should contain the search term
      const visibleJobs = page.locator('[data-testid="job-card"]');
      const count = await visibleJobs.count();
      
      for (let i = 0; i < count; i++) {
        const jobText = await visibleJobs.nth(i).textContent();
        expect(jobText?.toLowerCase()).toContain(searchTerm.toLowerCase());
      }
    }
  });

  test('search with no results shows empty state', async ({ page }) => {
    await page.goto('/');
    
    const searchInput = page.getByPlaceholder(/search/i).or(page.locator('[data-testid="search-input"]'));
    await expect(searchInput).toBeVisible();
    
    // Search for something that definitely doesn't exist
    await searchInput.fill('xyznonexistentfile123');
    await page.waitForTimeout(500);
    
    // Should show empty state or "no results" message
    await expect(
      page.getByText(/no.*results|no.*jobs.*found|nothing.*found/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('clear search shows all jobs again', async ({ page }) => {
    await page.goto('/');
    
    const initialCount = await page.locator('[data-testid="job-card"]').count();
    
    const searchInput = page.getByPlaceholder(/search/i).or(page.locator('[data-testid="search-input"]'));
    await searchInput.fill('test');
    await page.waitForTimeout(500);
    
    const filteredCount = await page.locator('[data-testid="job-card"]').count();
    
    // Clear search
    await searchInput.clear();
    await page.waitForTimeout(500);
    
    // Should show all jobs again
    const finalCount = await page.locator('[data-testid="job-card"]').count();
    expect(finalCount).toBe(initialCount);
  });
});

test.describe('Job Filters', () => {
  test('filter jobs by status', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Find status filter dropdown
    const statusFilter = page.locator('[data-testid="status-filter"]')
      .or(page.getByLabel(/filter.*status/i));
    
    if (await statusFilter.isVisible()) {
      await statusFilter.click();
      
      // Select "Complete" filter
      const completeOption = page.getByRole('option', { name: /complete/i })
        .or(page.getByText(/^complete$/i));
      await completeOption.click();
      
      await page.waitForTimeout(500);
      
      // All visible jobs should have "Complete" status
      const visibleJobs = page.locator('[data-testid="job-card"]');
      const count = await visibleJobs.count();
      
      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const statusBadge = visibleJobs.nth(i).locator('[data-testid="status-badge"]');
          await expect(statusBadge).toContainText(/complete/i);
        }
      }
    }
  });

  test('filter jobs by date range', async ({ page }) => {
    await page.goto('/');
    
    // Find date filter
    const dateFilter = page.locator('[data-testid="date-filter"]')
      .or(page.getByLabel(/filter.*date/i));
    
    if (await dateFilter.isVisible()) {
      await dateFilter.click();
      
      // Select "This Week" or similar option
      const weekOption = page.getByRole('option', { name: /this week/i })
        .or(page.getByText(/this week/i));
      
      if (await weekOption.isVisible()) {
        await weekOption.click();
        await page.waitForTimeout(500);
        
        // Should show some jobs or empty state
        const hasJobs = await page.locator('[data-testid="job-card"]').count() > 0;
        const hasEmptyState = await page.getByText(/no.*jobs/i).isVisible();
        
        expect(hasJobs || hasEmptyState).toBeTruthy();
      }
    }
  });
});
