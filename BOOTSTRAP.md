# Selenite Bootstrap Guide

This file is the single source of truth for getting the Selenite dev stack running from any state. **These directions are to be executed exactly as written—do not summarize or paraphrase them. If you are an AI agent, treat every command as something you must run.** If **any** command fails, stop and fix the noted issue instead of guessing or looping.

## Quick start (preferred)

1. Open PowerShell and `cd D:\Dev\projects\Selenite`.
2. Run the automated bootstrap script:
   ```powershell
   .\scripts\bootstrap.ps1
   ```
   This performs the pre-flight cleanup, installs dependencies, and launches backend + frontend production servers (the frontend command builds before serving). Watch those windows for live logs.
   - Default binding is now `0.0.0.0` (all interfaces). The script picks an advertised API host automatically (prefers Tailscale IP, then LAN). Ensure Windows Firewall allows inbound 8100/5173 if you want LAN/Tailscale access.
  - To advertise multiple hosts (e.g., `127.0.0.1`, your LAN IP, and a Tailscale IP), pass `-AdvertiseHosts 127.0.0.1,<LAN-IP>,100.x.y.z` (or use `scripts/start-selenite.ps1 -AdvertiseHosts ...`). Bootstrap will add each host to CORS, and the frontend falls back to whichever host you used to load it.

If you cannot run PowerShell scripts (policy, different shell, etc.), follow the manual steps below.

> Assumptions: Windows host, Python 3.10+, Node.js 18+, PowerShell shell. If you use another shell adjust path separators accordingly.

---

## 0. Pre-flight

1. **Open two PowerShell windows as the same user** (Backend / Frontend).
2. In *each* window: `cd D:\Dev\projects\Selenite`
3. Kill stray processes that may lock ports/files:
   ```powershell
   Get-ChildItem -Path logs -Filter *.log -Recurse | ForEach-Object { $_.IsReadOnly = $false }
   Get-Process python,node -ErrorAction SilentlyContinue | Stop-Process -Force
   ```

---

## 1. Backend API

All commands in **PowerShell Window 1**.

```powershell
cd backend
if (-not (Test-Path .\.venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-minimal.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
```
> Seed is idempotent and will not overwrite existing user passwords. If you need to reset the admin password intentionally, run `python scripts/reset_admin_password.py --password changeme` from the repo root instead of rerunning seed.

Then launch the API in production mode (disabling file logs avoids Windows log-lock issues):

```powershell
$env:DISABLE_FILE_LOGS = '1'
$env:ENVIRONMENT = 'production'
$env:ALLOW_LOCALHOST_CORS = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --host 127.0.0.1 --port 8100 --app-dir app
```

You should see `Uvicorn running on http://127.0.0.1:8100`.

**If uvicorn exits immediately:**
- *PermissionError on `selenite.log`*: delete `backend\logs\selenite.log` (if present) and retry with `DISABLE_FILE_LOGS=1`.
- *Port already in use*: `netstat -ano | findstr 8100`, then `Stop-Process -Id <PID> -Force`.

### Automated smoke test
After the backend window reports it is up, run the built-in backend smoke test to ensure `/health` and `/auth/login` behave correctly (this waits for readiness automatically):

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\smoke_test.py --base-url http://127.0.0.1:8100 --health-timeout 90
```

The script will exit with a non-zero status if the API is unhealthy or the `admin/changeme` seed account fails to log in.

---

## 2. Frontend production server

All commands in **PowerShell Window 2**.

```powershell
cd frontend
if (Test-Path node_modules) {
  attrib -R /S /D node_modules
}
npm install
npm run start:prod
```

You should see Vite output with `Local: http://127.0.0.1:5173/`.

**If npm install fails with EACCES / permission errors:**
- Close editors/terminals touching `node_modules`.
- Remove and reinstall:
  ```powershell
  rmdir node_modules -Recurse -Force
  npm cache clean --force
  npm install
  ```
- Ensure PowerShell is “Run as Administrator” if corporate AV enforces ACLs.

**If Vite cannot bind 5173:**
- `netstat -ano | findstr 5173` and kill the listed PID (`Stop-Process -Id ...`).

---

## 3. Optional: start both via E2E harness

If you want one command that boots backend + frontend + waits for readiness (useful for automation):

```powershell
cd frontend
npm install
npm run e2e:wait-and-run
```

This runs `scripts/start-backend-e2e.js` (with virtualenv detection, DB seeding, and log suppression), launches the production preview server on `127.0.0.1:5173`, waits for `/health`, and then executes Playwright. Hit `Ctrl+C` once to stop all processes.

---

## 4. Troubleshooting quick reference

| Symptom | Resolution |
|---------|------------|
| `selenite.log cannot be renamed` | Ensure backend isn’t already running; delete `backend\logs\selenite.log`; set `DISABLE_FILE_LOGS=1`. |
| `EACCES` on `.cross-env-*` | Reset node_modules attributes, remove the folder, reinstall, possibly elevate shell. |
| Backend 401s from frontend | Ensure Vite uses `--host 127.0.0.1` so it matches the backend CORS origin. |
| Playwright/AI instructions needed | Point the agent to this file; it includes all necessary startup commands. |

---

## 5. Shut down

When done testing:
- Stop uvicorn with `Ctrl+C` in Window 1.
- Stop Vite with `Ctrl+C` in Window 2.
- Clear env vars if desired (`Remove-Item Env:DISABLE_FILE_LOGS`).

This leaves the workspace clean for the next run (human or AI).
