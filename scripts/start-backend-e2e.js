#!/usr/bin/env node
/**
 * Cross-platform helper to launch the backend API for Playwright E2E runs.
 * Prefers the project virtualenv (POSIX or Windows); falls back to system python.
 */

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const backendRoot = path.resolve(__dirname, '..', 'backend');
const posixPython = path.join(backendRoot, '.venv', 'bin', 'python');
const windowsPython = path.join(backendRoot, '.venv', 'Scripts', 'python.exe');

let pythonCmd;
if (process.platform === 'win32') {
  pythonCmd = fs.existsSync(windowsPython) ? windowsPython : 'python';
} else if (fs.existsSync(posixPython)) {
  pythonCmd = posixPython;
} else {
  pythonCmd = 'python3';
}

const host = process.env.BACKEND_HOST || '127.0.0.1';
const port = process.env.BACKEND_PORT || '8100';
const timeoutMs = Number(process.env.BACKEND_TIMEOUT || 900_000);

const uvicornArgs = [
  '-m',
  'uvicorn',
  'app.main:app',
  '--host',
  host,
  '--port',
  port,
  '--app-dir',
  path.join(backendRoot, 'app'),
  '--no-access-log',
];

const envEnvironment = process.env.E2E_ENVIRONMENT || process.env.ENVIRONMENT || 'production';
const disableFileLogs = process.env.DISABLE_FILE_LOGS || '1';
const childEnv = {
  ...process.env,
  ENVIRONMENT: envEnvironment,
  DISABLE_FILE_LOGS: disableFileLogs,
  ALLOW_LOCALHOST_CORS: process.env.ALLOW_LOCALHOST_CORS || '1',
  E2E_FAST_TRANSCRIPTION: process.env.E2E_FAST_TRANSCRIPTION || '1',
  FORCE_QUEUE_START: process.env.FORCE_QUEUE_START || '1',
  DISABLE_RATE_LIMIT: process.env.DISABLE_RATE_LIMIT || '1',
  PYTHONPATH: backendRoot,
};

console.log(`[start-backend-e2e] Using python: ${pythonCmd}`);
console.log(`[start-backend-e2e] ENVIRONMENT=${envEnvironment}, DISABLE_FILE_LOGS=${disableFileLogs}`);
console.log('[start-backend-e2e] Seeding E2E database...');
const seedResult = spawnSync(pythonCmd, ['-m', 'app.seed_e2e', '--clear'], {
  stdio: 'inherit',
  cwd: backendRoot,
  env: childEnv,
});
if (seedResult.status !== 0) {
  console.error('[start-backend-e2e] Failed to clear seed database.');
  process.exit(seedResult.status ?? 1);
}
const seedPopulate = spawnSync(pythonCmd, ['-m', 'app.seed_e2e'], {
  stdio: 'inherit',
  cwd: backendRoot,
  env: childEnv,
});
if (seedPopulate.status !== 0) {
  console.error('[start-backend-e2e] Failed to seed database.');
  process.exit(seedPopulate.status ?? 1);
}
console.log('[start-backend-e2e] Seed complete. Starting uvicorn...');

const child = spawn(pythonCmd, uvicornArgs, {
  stdio: 'inherit',
  cwd: backendRoot,
  env: childEnv,
});

const timer = setTimeout(() => {
  console.warn(`[start-backend-e2e] Timeout hit (${timeoutMs}ms). Stopping backend.`);
  child.kill('SIGTERM');
}, timeoutMs);

const cleanup = () => {
  clearTimeout(timer);
  if (!child.killed) {
    child.kill('SIGTERM');
  }
};

process.on('SIGINT', () => {
  cleanup();
  process.exit(130);
});
process.on('SIGTERM', () => {
  cleanup();
  process.exit(143);
});

child.on('exit', (code, signal) => {
  clearTimeout(timer);
  if (signal) {
    console.log(`[start-backend-e2e] Backend exited with signal ${signal}`);
  }
  process.exit(code ?? 0);
});

child.on('error', (err) => {
  clearTimeout(timer);
  console.error('[start-backend-e2e] Failed to start backend:', err);
  process.exit(1);
});
