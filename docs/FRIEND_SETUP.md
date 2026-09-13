# Friend tester setup (Path A — shared Railway board)

## Live URLs

- Timing API: https://dsr-eventlab-timing-production.up.railway.app
- Public Time Attack (How To Use teaser): https://doomsantos.github.io/eventlab-codes/leaderboard.html  
  (after you push this commit to GitHub Pages)

## Send your friend

1. Zip: `dist/DSR-Lap-Collector.zip` (from repo after build)
2. One invite code (from `server/.invites.txt` — private, do not commit)
3. These steps:

### Friend steps

1. Unzip anywhere  
2. Run `DSR-Lap-Collector.exe` (Windows may warn — More info → Run anyway)  
3. Browser opens http://127.0.0.1:8765 — API URL should already be Railway  
4. Paste invite + choose display name → **Claim invite**  
5. FH6 → Data Out **On** → IP `127.0.0.1` → Port `9876`  
6. Drive — Clean laps appear on the live board  

## You: mint more invites

**Easiest:** double-click `mint-invite.bat` in the project folder.  
It prints a new invite code and appends it to `server\.invites.txt`.

Or run this in PowerShell from the project folder:

```powershell
$admin = Get-Content -Raw server\.admin_token
Invoke-RestMethod -Method Post `
  -Uri "https://dsr-eventlab-timing-production.up.railway.app/v1/admin/invites" `
  -Headers @{ Authorization = "Bearer $admin" } `
  -ContentType "application/json" -Body "{}"
```

## Rebuild exe after code changes

```powershell
powershell -File scripts/build_collector_exe.ps1
Compress-Archive -Path dist\DSR-Lap-Collector\* -DestinationPath dist\DSR-Lap-Collector.zip -Force
```
