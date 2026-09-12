# PROJECT ROADMAP — DSR EventLab Codes + Timing Board

## Product

Static EventLab **codes** site + **PC collector** (FH6 Data Out) → **timing API** → lab/public board (24h, live presence, history).

## Phases

| Phase | Status | Notes |
|-------|--------|-------|
| Codes site (GitHub Pages) | Done | `data/tracks.json` driven |
| PC collector + local SQLite export | Done | `python -m collector` |
| Lap integrity Clean/Paused/Rewound | Done | Albert Park batches |
| Albert Park fingerprint/verify | Done | `collector.verify` |
| Timing API (invite auth, upload, 24h, live) | **Done (local)** | `python -m server` |
| Collector claim + auto-upload + presence | **Done** | `collector/device.json` |
| Private lab board wired to API | **Done** | `board-lab.html` + `board-live.js` |
| Board UX (car names, best+expand) | **Done** | CD playtest OK |
| Deploy hardening (env, CORS, Docker, docs) | **Done** | Waiting CD Railway/Fly account to go live |
| Albert Park auto-track | **Done** | Fingerprint sets track after matched lap |
| Production API host go-live | **Done** | Railway `dsr-eventlab-timing-production.up.railway.app` |
| Public leaderboard unveil | **Done** | Live 24h board on `leaderboard.html` |
| Friend collector exe | **Done** | `dist/DSR-Lap-Collector.zip` + invite |
| Player history page | Later | API `/v1/history` exists |
| Mobile companion | Deferred | Same API later |

## Next

1. Send friend the zip + invite (`docs/FRIEND_SETUP.md`).
2. More track fingerprints as captures land.
3. Optional: GitHub autodeploy from Railway linked repo.

## Fidelity / debt

| Item | Status |
|------|--------|
| Invite-only auth (not Xbox) | Engineering default — CD can override |
| Paused not on public 24h board | Same as rewound for ranking |
| Open registration | Not built |
| Production hostname | Ready to deploy; URL unknown until CD hosts |
| Shape-compare tool | Outside repo (`albert-park-shape-compare`) — do not commit |

## Batch log

- **2026-09-12 Lead onboarding:** AGENTS / playbook / PRODUCT_BRIEF; timing `server` package; collector cloud claim/auto-upload/presence; lab board → API.
- **2026-09-12 Board UX:** car names on API/board; best-per-driver 24h list with expandable lap history.
- **2026-09-12 Playtest green:** CD confirmed uploads, rewind detect, board UX.
- **2026-09-12 Deploy + auto-track:** env/CORS/Docker/DEPLOY.md; Albert Park fingerprint auto-sets track.
- **2026-09-12 Auto-track fix:** per-lap track tagging, live match thresholds, UI no longer sticks on manual Monza, detect status in collector.
- **2026-09-12 Upload id fix:** unique client_lap_id so collector restarts stop silently dropping new cloud laps.
