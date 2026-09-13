# PROJECT ROADMAP — DSR EventLab Codes + Timing Board

## Product

Static EventLab **codes** site + **PC collector** (FH6 Data Out) → **timing API** → **Time Attack** (Live Timing / Leaderboards / profiles). Spec: `docs/TIME_ATTACK.md`.

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
| Public Time Attack teaser + nav | **Done** | How To Use teaser; Track Codes \| Time Attack |
| Doom metal site theme | **Done** | Banner + title arts; live on GitHub Pages |
| Public Live Timing / Leaderboards unveil | Waiting TA | After EventLab codes + fingerprints |
| Time Attack product spec | **Locked** | `docs/TIME_ATTACK.md` |
| Player profile pages | Planned | Full TA history; after Live/Leaderboard shapes |
| Mobile companion | Deferred | Same API later |

## Next

1. **CD:** create TA EventLab events (offset start, ~50 laps, one code/track); optional higher-res banner (≥1920px).  
2. Fingerprint TA → count only those laps → unveil Live Timing + Leaderboards (replace teaser).  
3. List TA codes under Track Codes as Time Attack variant; player profiles later.

## Fidelity / debt

| Item | Status |
|------|--------|
| Invite-only auth (not Xbox) | Engineering default — CD can override |
| Paused not on public 24h board | Same as rewound for ranking |
| Open registration | Not built |
| Production hostname | Railway live (`dsr-eventlab-timing-production.up.railway.app`) |
| Shape-compare tool | Outside repo (`albert-park-shape-compare`) — do not commit |
| Microsoft / Xbox OAuth | Deferred — analysis in `docs/MICROSOFT_OAUTH_NOTES.md` |

## Batch log

- **2026-09-12 Lead onboarding:** AGENTS / playbook / PRODUCT_BRIEF; timing `server` package; collector cloud claim/auto-upload/presence; lab board → API.
- **2026-09-12 Board UX:** car names on API/board; best-per-driver 24h list with expandable lap history.
- **2026-09-12 Playtest green:** CD confirmed uploads, rewind detect, board UX.
- **2026-09-12 Deploy + auto-track:** env/CORS/Docker/DEPLOY.md; Albert Park fingerprint auto-sets track.
- **2026-09-12 Auto-track fix:** per-lap track tagging, live match thresholds, UI no longer sticks on manual Monza, detect status in collector.
- **2026-09-12 Upload id fix:** unique client_lap_id so collector restarts stop silently dropping new cloud laps.
- **2026-09-13:** CD parked Microsoft/Xbox OAuth analysis in `docs/MICROSOFT_OAUTH_NOTES.md`.
- **2026-09-13:** Time Attack IA + rules locked (`docs/TIME_ATTACK.md`); recommend new Lead chat for teaser + nav.
- **2026-09-13:** Public Time Attack How To Use teaser + nav shell (Track Codes | Time Attack); Live Timing / Leaderboards gated until TA codes.
- **2026-09-13:** Doom fantasy / doom metal theme live (banner hero, Track Codes / Time Attack title arts).
