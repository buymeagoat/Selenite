# Manual Verification Guide

## [SETTINGS-STORE] Shared Settings Provider

1. **Bootstrap & Login**  
   - Run `./scripts/start-selenite.ps1` (or your wrapper) to launch backend + frontend.  
   - Open the app in a new browser window/tab and log in as `admin`.

2. **Verify Settings Page**  
   - Navigate to Settings (/settings).  
   - Change the Default Model and Default Language, click **Save**, refresh, and confirm the values persist.  
   - Change the Default Diarizer. Options that cannot run on this system must appear greyed out with a note (e.g., "GPU required"). Save and refresh to ensure the selection sticks.  
   - If you need to debug, open DevTools -> Console and run window.__SELENITE_SETTINGS_DEBUG__ to dump the cached settings events.

3. **New Job Modal Behavior**  
   - Click "+ New Job."  
   - Model and language selects should match the admin defaults, and the timestamps checkbox should be checked.  
   - "Detect speakers" must stay enabled whenever at least one diarization backend is available; the dropdown lists every backend, greying out unavailable ones with their notes.  
   - If no diarization models are viable, the checkbox must be disabled with helper text ("No compatible diarization models...").

4. **Failure Simulation (optional)**  
   - Stop the backend or disconnect networking; the modal should show "Unable to verify diarization availability; using safe defaults" but still allow job creation.  
   - Restore connectivity and reopen the modal to confirm the helper text clears and the dropdown repopulates.

Record the date/result in `docs/build/PRODUCTION_TASKS.md` under `[SETTINGS-STORE]` once verified.  

---

## [SYSTEM-ENDPOINTS] Authenticated system API spot-check

1. **Fetch a token**  
   - Run `./scripts/get-auth-token.ps1 -Username admin -ShowExample`.  
   - When prompted, enter the current admin password. Copy the printed bearer token (it lives in local storage under `auth_token` too if you prefer).
2. **Call availability API**  
   - PowerShell: `Invoke-RestMethod -Uri "http://127.0.0.1:8100/system/availability" -Headers @{ Authorization = "Bearer <token>" }`.  
   - Confirm the JSON lists diarizers with accurate `available` flags for the host (GPU-required weights should be `available:false` on CPU-only machines).
3. **Call system info API**  
   - `Invoke-RestMethod -Uri "http://127.0.0.1:8100/system/info" -Headers @{ Authorization = "Bearer <token>" }`.  
   - Verify CPU/RAM/disk/network data matches the Settings -> System card.
4. **Document results**  
   - Note the date, command used, and any discrepancies back in `docs/build/PRODUCTION_TASKS.md` under `[AVAIL-ENDPTS]`.

---

## [BACKUP-VERIFY] Pre-release backup verification

1. **Run backup + restore verification**  
   - Execute `./scripts/backup-verify.ps1` from the repo root.  
   - Confirm it prints "Backup and restore verification complete."
   - The restore target is always under `scratch/` and does not overwrite live models or logs.

2. **Record evidence**  
   - Note the backup path and timestamp in `docs/build/PRODUCTION_TASKS.md`.  
   - If any mismatches appear, stop and resolve before merging to `main`.

---

## [RELEASE-UI] Post-release UI verification

1. **Login**  
   - Open the app and log in as `admin`.

2. **Existing data**  
   - Confirm recent jobs and tags are visible.

3. **Create a job**  
   - Upload a small file and confirm the job enters the queue.

4. **Export check**  
   - Open a completed job and export a transcript.

5. **Record outcome**  
   - Log results in `docs/build/PRODUCTION_TASKS.md`.
