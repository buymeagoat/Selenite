import { afterEach, vi } from 'vitest';
import '@testing-library/jest-dom';

// Vitest setupFiles run outside the test environment globals unless imported.
// Use direct execution with spies instead of beforeAll/afterAll.

const defaultFetch = vi.fn().mockResolvedValue({
  ok: true,
  status: 200,
  statusText: 'OK',
  json: async () => ({}),
});

const ensureDefaultFetch = () => {
  if (typeof globalThis !== 'undefined') {
    globalThis.fetch = defaultFetch as typeof fetch;
  }
};

const ensureAnchorClickStub = () => {
  if (typeof HTMLAnchorElement === 'undefined') {
    return;
  }
  const anchorProto = HTMLAnchorElement.prototype as HTMLAnchorElement & { __seleniteMocked?: boolean };
  if (anchorProto.__seleniteMocked) {
    return;
  }
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  anchorProto.__seleniteMocked = true;
};

ensureDefaultFetch();
ensureAnchorClickStub();

afterEach(() => {
  ensureDefaultFetch();
  vi.useRealTimers();
  vi.clearAllTimers();
  if (typeof localStorage !== 'undefined') {
    localStorage.clear();
  }
});

if (typeof window !== 'undefined') {
  if (!('alert' in window)) {
    // @ts-ignore
    window.alert = () => {};
  }
  if (!('prompt' in window)) {
    // @ts-ignore
    window.prompt = () => '';
  }
  if (!('confirm' in window)) {
    // @ts-ignore
    window.confirm = () => true;
  }
  if (!('isAlertMocked' in (window as any))) {
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.spyOn(window, 'prompt').mockImplementation(() => 'test');
    vi.spyOn(window, 'confirm').mockImplementation(() => true);
    (window as any).isAlertMocked = true;
  }
}

