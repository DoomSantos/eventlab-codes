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
| Public Live Timing / Leaderboards unveil | Waiting CD | Fingerprints + codes staged; hold until CD unveil |
| Time Attack product spec | **Locked** | `docs/TIME_ATTACK.md` |
| Player profile pages | Planned | Full TA history; after Live/Leaderboard shapes |
| Mobile companion | Deferred | Same API later |

## Next

1. **CD unveil gate:** TA codes staged in `data/time-attack-codes.json` (not live). When CD says go → Track Codes TA variant + How To Use codes + Live Timing / Leaderboards.  
2. **Invites:** IG reel pre-signup → note DMs → batch-mint on launch (see `docs/PRODUCT_BRIEF.md`).  
3. Player profiles later.

## Fidelity / debt

| Item | Status |
|------|--------|
| Invite-only auth (not Xbox) | Engineering default — CD can override |
| Invite distribution | Launch: IG pre-signup list → batch mint+DM; IG Messaging auto-bot deferred |
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
- **2026-09-14:** TA start fingerprint + integrity fixes playtest green; server `mode`; AEST windows + `/v1/leaderboard`.
- **2026-09-14:** Monaco TA auto-ID confirmed; Top Gear TA + soft-corridor runway fingerprint shipped.
- **2026-10-23:** Brands Hatch Indy + GP TA start fingerprints shipped (2 pit slots each; 2 km layout window). First GP batch was Indy-length and was set aside.
- **2026-10-23:** CD playtest green — Brands Hatch Circuit and Indy auto-ID as Time Attack with the correct layout name.
- **2026-10-23:** Public collector driver UI tightened (setup + troubleshooting; claim form hides after sign-in; lab stays on `?lab=1`).
- **2026-10-23:** Unlisted Live Timing + Leaderboards pages on GitHub Pages for tester links; How To Use / TA buttons unchanged.
- **2026-10-23:** Live Timing / Leaderboards track filters include all 7 TA tracks (names only; Brands Hatch Circuit + Indy added). Share codes still unpublished.
- **2026-10-23:** Board filter dropdowns restyled dark (no white OS menus). Brands Hatch EventLab (non-TA) codes still waiting on CD lap lists.
- **2026-10-23:** Brands Hatch Circuit + Indy EventLab codes live on Track Codes (With/Without Drivatars, 5/15/25/50). Time Attack codes still unpublished.
- **2026-10-23:** Replacement invites: `reissue-invite.bat` + `list-players.bat` reattach a new PC to an existing display name (Railway redeploy needed).
- **2026-10-23:** Playtest fix — Who's Racing was Albert Park in FH6 open world (`is_race_on` + default track). Presence now requires `mode=time_attack`. Clean non-TA laps were uploading with empty mode so Live Timing / Leaderboards stayed empty; auto-upload is TA-only.
- **2026-10-23:** TA start now matches after a festival→EventLab teleport. CD's Albert Park TA session was bundled with open-world path so the pit grid sat mid-lap and never armed Mode. Matcher splits on 1500 m+ jumps; detector drops the festival path. Tonight's clean TA laps backfilled to the live board.
- **2026-10-24:** Monza GP vs Junior — later laps from the start/finish were tagged Junior. Offset-start now locks the layout for the session. Mislabeled GP-length Junior times retagged on the live board. Collector dist rebuilt.
- **2026-10-24:** Public README is Time Attack tester docs only. Windows zip published as a GitHub Release (no device token, no staged share codes).
