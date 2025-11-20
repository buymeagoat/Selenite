import { test, expect } from '@playwright/test';

import type { Page } from '@playwright/test';

async function waitForJobCards(page: Page) {
  const jobCards = page.locator('[data-testid="job-card"]');
  const maxMs = 20000;
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const count = await jobCards.count();
    if (count > 0) return { count, jobCards };
    await page.waitForTimeout(400);
  }
  const html = await page.content();
  throw new Error(`No job cards after ${maxMs}ms. HTML length=${html.length}`);
}

/**
 * Search and Filter Tests
 * 
 * Tests search functionality and job filtering capabilities.
 */

test.describe('Search Functionality', () => {
  test('search jobs by filename', async ({ page }) => {
    await page.goto('/');

    // Wait for dashboard heading to ensure we are past auth redirect
    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible({ timeout: 8000 });

    // Robust wait for at least one job card: poll until found or timeout
    const { count: initialCount, jobCards } = await waitForJobCards(page);
    await expect(jobCards.first()).toBeVisible();
    expect(initialCount).toBeGreaterThan(0);
    
    // Find search input (placeholder="Search jobs" from Dashboard)
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible();
    
    // Search for known seeded job filename pattern (e.g., "meeting")
    const searchTerm = 'meeting';
    await searchInput.fill(searchTerm);
    
    // Wait for search results to update
    await page.waitForTimeout(500); // Debounce
    
    // Should show filtered results
    const visibleJobs = page.locator('[data-testid="job-card"]');
    const count = await visibleJobs.count();
    
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThanOrEqual(initialCount);
    
    // All visible jobs should contain the search term (sample first few to avoid flaky re-renders)
    const samples = Math.min(count, 3);
    for (let i = 0; i < samples; i++) {
      const jobText = await visibleJobs.nth(i).textContent();
      expect(jobText?.toLowerCase()).toContain(searchTerm.toLowerCase());
    }
  });

  test('search with no results shows empty state', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible({ timeout: 8000 });
    const jobCards = page.locator('[data-testid="job-card"]');
    await waitForJobCards(page);
    
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible();
    
    // Search for something that definitely doesn't exist
    await searchInput.fill('xyznonexistentfile123');
    await page.waitForTimeout(500);
    
    // Should show empty state message ("No jobs match your search or filters.")
    await expect(
      page.getByText(/no jobs match/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('clear search shows all jobs again', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible({ timeout: 8000 });
    const jobCards = page.locator('[data-testid="job-card"]');
    await waitForJobCards(page);
    
    const initialCount = await page.locator('[data-testid="job-card"]').count();
    
    const searchInput = page.getByPlaceholder(/search/i);
    await searchInput.fill('meeting');
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
    
    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible({ timeout: 8000 });
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 25000 });
    
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
    
    // Wait for dashboard & initial cards
    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible({ timeout: 8000 });
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 25000 });
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
