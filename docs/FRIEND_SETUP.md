# Friend tester setup (Path A — shared Railway board)

## Live URLs

- Timing API: https://dsr-eventlab-timing-production.up.railway.app
- Public Time Attack (How To Use teaser): https://doomsantos.github.io/eventlab-codes/leaderboard.html  
  (after you push this commit to GitHub Pages)

## Send your friend

1. Zip: GitHub Release `DSR-Lap-Collector.zip` (https://github.com/DoomSantos/eventlab-codes/releases/latest)
2. One invite code (from `server/.invites.txt` — private, do not commit)
3. These steps:

### Friend steps

1. Unzip anywhere  
2. Run `DSR-Lap-Collector.exe` (if Windows says it protected your PC: **More info → Run anyway**)  
3. Leave that window open. A browser should open http://127.0.0.1:8765 — follow **Setup** on the page  
4. Paste invite + display name → **Claim invite**  
5. FH6 → Data Out **On** → IP `127.0.0.1` → Port `9876` (avoid 5200–5300)  
6. Drive a Time Attack EventLab from the pit / offset start — status **Game connected**; Clean laps upload alone  

If something fails, use **Troubleshooting** on the same page (Waiting for game, Rewound, uploads).

Research / path captures (you, not friends): `http://127.0.0.1:8765/?lab=1`

## Launch invite wave (CD process)

1. Post an Instagram reel for **pre-signup** — interested drivers DM you.  
2. Keep a simple list of who messaged.  
3. On launch day: run `mint-invite.bat` (or admin API) in a batch and DM codes out together.  
4. After launch: see how often people still ask; stay manual unless volume hurts.  

IG Messaging API auto-mint is **deferred** — see `docs/PRODUCT_BRIEF.md`.

## You: mint more invites

**New player:** double-click `mint-invite.bat`.  
It prints a new invite code and appends it to `server\.invites.txt`.

**Same player, new PC / reset collector:**  
1. Double-click `list-players.bat` and copy their display name exactly.  
2. Double-click `reissue-invite.bat`, paste that name.  
3. DM them the new invite. They claim it with the **same** display name.  
Old times stay on the board; the old PC stops uploading.

Or run this in PowerShell from the project folder:

```powershell
$admin = Get-Content -Raw server\.admin_token
Invoke-RestMethod -Method Post `
  -Uri "https://dsr-eventlab-timing-production.up.railway.app/v1/admin/invites" `
  -Headers @{ Authorization = "Bearer $admin" } `
  -ContentType "application/json" -Body "{}"
```

## Rebuild exe after code changes

The spec ships `data/tracks.json`, `data/time-attack-tracks.json`, `data/time-attack-codes.json`, `data/default-api.json`, cars, and **all** `data/fingerprints/*.json`.

```powershell
powershell -File scripts/build_collector_exe.ps1
Compress-Archive -Path dist\DSR-Lap-Collector\* -DestinationPath dist\DSR-Lap-Collector.zip -Force
```
