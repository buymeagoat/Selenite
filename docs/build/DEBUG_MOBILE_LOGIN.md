# Debugging Mobile Login Issues

These steps assume the application is running via `scripts/start-selenite.ps1` and the tester is trying to access it from a phone on the same LAN or over Tailscale.

---

## 1. Confirm the host IP and listener status
1. Run `\.\test-network-access.ps1`.  
  - It prints every non-loopback IPv4 address detected (LAN + Tailscale) and whether port 8100 is listening.  
  - It also probes `http://127.0.0.1:8100/health` and `http://<LAN_IP>:8100/health` so you immediately know if Windows Firewall is blocking remote access.
2. If the network probe fails, follow the script’s prompt to run `\.\allow-backend-port.ps1` from an elevated PowerShell window and re-run the test.
3. Share the reported LAN/Tailscale IPs with whoever is testing (e.g., `http://192.168.x.x:5173/`).
4. When restarting via the helpers, explicitly advertise each host you plan to share: `.\scripts\bootstrap.ps1 -AdvertiseHosts 127.0.0.1,<LAN-IP>,100.x.y.z` (or `.\scripts\start-selenite.ps1 -AdvertiseHosts ...`). This keeps backend CORS + frontend routing aligned no matter which address the tester loads.

## 2. Verify CORS configuration
`.\scripts\test-cors.ps1 -HostIp <LAN_IP>` exercises the `/health` endpoint with an `Origin` header that matches the frontend URL. Successful output shows the HTTP status and whether `Access-Control-Allow-Origin` is returned. If it is missing, update `backend/.env` (`CORS_ORIGINS`) and restart via `scripts/start-selenite.ps1`.

## 3. Capture what the mobile browser sees
Ask the tester to:
- Open the normal UI at `http://<LAN_IP>:5173/`.
- Attempt a login.
- If an error banner appears, expand the “Technical details” drawer and screenshot it. That payload mirrors what the frontend logs to the console.
- (Optional) On iOS Safari, enable Web Inspector (Settings → Safari → Advanced → Web Inspector) and connect to a Mac to inspect the console.

## 4. Watch server-side logs in real time
```
.\scripts\view-logs.ps1 -Follow -Filter "LOGIN|AUTH|CLIENT"
```
This surfaces backend login attempts, rate-limit warnings, and any diagnostics forwarded by the browser. Use `-ShowAll` if you need the raw log stream.

## 5. Optional: authenticated diagnostics endpoints
Diagnostics routes now require an admin token. If you need to probe them manually, reuse an access token from a recent login or mint one via a short Python snippet that imports `create_access_token`. Example PowerShell:
```powershell
$token = "<paste bearer token>"
Invoke-RestMethod http://<LAN_IP>:8100/diagnostics/info `
  -Headers @{ Authorization = "Bearer $token" }
```
The payload intentionally excludes raw headers so secrets never leak to the browser.

## 6. Common failure signatures
- `Failed to fetch` (frontend toast): network path/firewall problem; rerun step 1.
- `CORS policy: No 'Access-Control-Allow-Origin' header`: backend `CORS_ORIGINS` missing the frontend origin seen in the browser.
- `Incorrect username or password`: backend handled the request correctly; verify credentials or reset via `python scripts/reset_admin_password.py --password changeme`.
- `[CLIENT ERROR]` logs: check `view-logs.ps1` output for stack traces forwarded from the browser.

Keep these steps in `docs/build/PRODUCTION_TASKS.md` synced: if a new diagnostic option is added (e.g., mobile-only logging), document it here and reference the task ID for traceability.
