# Mobile Login Debugging – Quick Card

Use this when someone on a phone/tablet says “login failed” or “nothing loads.”

1. **Run the two network helpers locally**
   ```powershell
   .\test-network-access.ps1
   .\test-cors.ps1 -HostIp <LAN_IP_FROM_STEP1>
   ```
   These confirm ports 5173/8100 are reachable and CORS is configured for that origin.

2. **Keep server logs streaming**
   ```powershell
   .\view-logs.ps1 -Follow -Filter "LOGIN|AUTH|CLIENT"
   ```
   You will immediately see POST /auth/login attempts plus any `[CLIENT ERROR]` lines emitted by the browser.

3. **Have the tester capture client details**
   - Open `http://<LAN_IP>:5173/` (not a special debug page).
   - After the error appears, expand the “Technical details” disclosure on the toast and screenshot it.
   - If they can use desktop Safari DevTools (Web Inspector), capture the console output too.

4. **Reset credentials if needed**
   ```powershell
   python .\scripts\reset_admin_password.py --password changeme
   ```
   Then kill/restart via `.\start-selenite.ps1` so both backend and frontend reload the new password.

5. **(Optional) Probe authenticated diagnostics**
   ```powershell
   $token = "<Bearer token from Login response>"
   Invoke-RestMethod http://<LAN_IP>:8100/diagnostics/info -Headers @{ Authorization = "Bearer $token" }
   ```
   These routes are admin-only; share results securely since they include client IP/user agent.

When the issue is resolved, memorialize the root cause in `docs/build/PRODUCTION_TASKS.md` under the relevant task ID so future sessions know the historical fixes.
