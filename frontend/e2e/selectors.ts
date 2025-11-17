// Centralized selectors & data-test-id strategy for E2E tests.
// Prefer role & accessible name first; fall back to data-test-id only when necessary.
// Add data-test-id attributes in components if a stable accessible handle isn't feasible.

export const selectors = {
  login: {
    usernameInput: 'input#username', // using id for clarity
    passwordInput: 'input#password',
    submitButton: 'button[type="submit"]',
  },
  dashboard: {
    jobCard: '[data-test-id="job-card"]',
    newJobButton: '[data-test-id="new-job-btn"]',
    searchInput: '[data-test-id="search-input"]'
  },
  tags: {
    tagInput: '[data-test-id="tag-input"]',
    tagList: '[data-test-id="tag-list"]'
  }
};
