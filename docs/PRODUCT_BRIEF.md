# Product brief — PC collector → timing board

**Brand:** doomsantosracing (DSR) EventLab codes + community timing.  
**Audience:** FH6 EventLab drivers using DSR share codes.

## Goal (current phase)

Safe, easy path: **PC collector** listens to FH6 Data Out → validates laps → **auto-uploads** to a timing API → public site shows **rolling 24h board**, **session/history**, and **who’s racing live**.

**Out of scope for now:** Android/iOS companion (same API later).

## Locked from Creative Director

| Topic | Decision |
|-------|----------|
| Platform | PC collector first |
| Timing buckets | Class + PI (e.g. `A 699`) |
| Assists | Not recorded |
| Xbox / MSA OAuth | Not for this phase |
| Codes site | GitHub Pages static (`data/tracks.json`) |
| Lap integrity | Clean / Paused / Rewound from UDP gaps (Albert Park proven) |
| Manual export | Still works locally; auto-upload is the next product path |

## Engineering defaults (not CD-locked — change if CD overrides)

| Topic | Default | Notes |
|-------|---------|-------|
| Who can upload | Invite code → long-lived device token | Safer than open POST; CD issues invites |
| Display name | Chosen at invite claim; unique (case-insensitive) | Shown on board; no Xbox link yet |
| Public board rows | **Clean** integrity only; **best per driver** on main list, expand for all 24h laps | Rewound/Paused kept in history but not ranked |
| Car column | Friendly name from `data/cars.json` when known | Falls back to `Car #ordinal` |
| Board window | Rolling **24 hours** by `submitted_at` | Older rows remain for personal history |
| Live presence | Heartbeat while collector has race-on packets | Expire ~45s after last beat |
| Abuse | Rate limits + invite one-time claim + time sanity bounds | See API section |
| Hosting | Local `python -m server`; deploy via Dockerfile — see `docs/DEPLOY.md` | Default target: Railway + volume for SQLite |
| CORS | Local `*`; production lock via `TIMING_CORS_ORIGINS` | Must include GitHub Pages origin |
| Track detect | Albert Park fingerprint auto-sets track after a matched lap | Other tracks still manual |
| Auth header | `Authorization: Bearer <device_token>` | |

## User journeys

### Claim identity (once per PC install)

1. CD gives player an invite code.
2. In collector: enter invite + display name → claim.
3. Collector stores device token locally; no re-login each session.

### Race + auto-upload

1. Player sets track (manual for now; fingerprint assist later).
2. Drives EventLab; collector detects completed laps + integrity.
3. **Clean** laps auto-upload when online; failures queue and retry.
4. Local SQLite / session list still works offline.

### Public site

1. `/leaderboard` (or dedicated board page) loads rolling 24h times from API.
2. Live strip: who’s racing which track (from presence).
3. Optional: player history page later.

## API sketch (`/v1`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/claim` | invite code | Create device + display name → token |
| POST | `/v1/laps` | Bearer | Upload one completed lap |
| GET | `/v1/board` | public | Rolling 24h Clean times (filter track / class_pi) |
| POST | `/v1/presence` | Bearer | Heartbeat: track, class_pi, car, racing bool |
| GET | `/v1/live` | public | Active racers (recent heartbeats) |
| GET | `/v1/history?player=` | public | That player’s recent uploads |

### Lap payload (upload)

- `track`, `lap_time_s`, `class_name`, `car_pi`, `car_ordinal`
- `integrity` (`clean` \| `paused` \| `rewound`)
- `stream_gaps`, optional `client_lap_id` (idempotency)
- Server stamps `submitted_at`; rejects absurd times / unknown tracks

### Abuse limits (v1 defaults)

- Invite: single use
- Uploads: 60 / hour / device (tunable)
- Presence: ignore > 1 heartbeat / 5s
- Lap time: reject ≤ 0 or > 30 minutes
- Only known track names from `data/tracks.json`

## Explicit debt / open CD questions

1. **Invite UX** — how CD distributes codes (Discord DM, etc.) — process, not code.
2. **Open registration later?** — not built until CD asks.
3. **Best-ever vs 24h-only** — v1 is 24h public board; all-time best can return later.
4. **Paused laps** — stored, not ranked (same as rewound for public board).
5. **Production host** — pick when local API is proven (Fly/Railway/CF Workers, etc.).
