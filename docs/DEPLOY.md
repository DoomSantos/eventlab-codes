# Deploy — timing API

GitHub Pages stays static (codes + lab board). The **timing API** (`python -m server`) needs a small always-on host.

## Local (already working)

```powershell
cd "C:\Users\clove\CursorProjects\DSR EventLab Codes Page"
python -m server --port 8787
```

Collector API URL: `http://127.0.0.1:8787`  
Lab board: `data/board-config.json` → same base URL

## Environment

| Variable | Purpose |
|----------|---------|
| `PORT` / `TIMING_PORT` | Listen port (Railway/Fly set `PORT`) |
| `TIMING_HOST` | Bind address (`0.0.0.0` when `PORT` is set) |
| `TIMING_DB` | SQLite file path (put on a **persistent volume**) |
| `TIMING_CORS_ORIGINS` | Comma-separated browser origins, e.g. `https://doomsantos.github.io,http://127.0.0.1:8080` |

Empty CORS = allow `*` (fine for local). Production should list your Pages origin only.

## Production (Railway)

- Project: `dsr-eventlab-timing`
- API: https://dsr-eventlab-timing-production.up.railway.app
- Volume mounted at `/data` (`TIMING_DB=/data/timing.db`)
- CORS: GitHub Pages + local preview
- Admin invites: `TIMING_ADMIN_TOKEN` + `POST /v1/admin/invites` (see `docs/FRIEND_SETUP.md`)

Redeploy from this folder:

```powershell
railway up -y -d --ci
```

## After go-live checklist

- [ ] Collector claimed against production URL  
- [ ] Lab board (`board-config.json`) uses production `apiBase`  
- [ ] CORS includes Pages origin  
- [ ] CD keeps invite codes private  
- [ ] Public `leaderboard.html` unveil when CD says go  

## Note on SQLite

Without a volume, cloud disks are wiped on redeploy — times vanish. Always attach persistent storage for `TIMING_DB`.
