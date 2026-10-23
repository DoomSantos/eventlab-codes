# Agent handover — DoomSantos Racing / Time Attack

## Copy-paste for a **new** Lead chat

```
You are Autonomous Lead Engineer. I am Creative Director.

OPERATING MODEL: C:\Users\clove\CursorProjects\Project Master Plan\AUTONOMOUS_LEAD_PLAYBOOK.md
Also follow this repo’s AGENTS.md / .cursorrules / PROJECT_ROADMAP.md / docs/PRODUCT_BRIEF.md / docs/TIME_ATTACK.md.

PRODUCT: DoomSantos Racing — EventLab Track Codes + Time Attack (PC collector → Railway API → Live Timing / Leaderboards)
WORKSPACE: C:\Users\clove\CursorProjects\DSR EventLab Codes Page

Use docs/agent-handover.md as LAST COMPLETED / NEXT if fresher than this message.

LAST COMPLETED: Monza layout lock; public README is Time Attack tester docs; Windows collector zip on GitHub Releases (no token, no staged codes).
NEXT: CD playtest latest Release zip — 3+ laps full Monza must stay GP. Unveil still gated.
OPEN DEBT: How To Use / TA buttons still teaser-gated; Microsoft OAuth deferred; default session end = midnight AEST unless CD overrides; banner currently ~1024px; IG invite wave is manual pre-signup
```

## LAST COMPLETED

- **2026-10-23 playtest fix:** Who's Racing was showing open-world driving as Albert Park (`is_race_on` + default track). `/v1/live` now requires `mode=time_attack`. Clean non-TA laps (today's Holden A 700 times) uploaded with empty mode so boards stayed empty — auto-upload is Clean Time Attack only. **Live dist rebuilt** `dist/DSR-Lap-Collector.exe` (zip without device token). CD must run this new exe, not the 5:47pm one.
- **2026-10-23 festival-load TA miss:** CD used Albert Park Time Attack; collector lap 1 kept open-world path then teleported onto the pit grid (3960 m). Offset-start matching only looked at the first 180 m so Mode never armed and laps 2+ (normal S/F) stayed off the board. Matcher now scores post-teleport windows; detector drops festival path. Five clean TA laps backfilled (best 1:48.036). Rewound 1:51 not uploaded.
- **2026-10-23 paddock spawn 1317 m:** next Albert Park TA session teleported 1317 m onto the pits (under the 1500 m integrity ignore) so Mode still did not arm, Who's Racing stayed empty, new laps stayed local. Spawn-jump window is now **500 m**. This session's clean laps backfilled (best **1:46.624**). Rewound laps not uploaded. Live dist rebuilt again.
- **Circuit de Monaco** TA auto-ID confirmed by CD
- **Top Gear Test Track** TA start fingerprint (6 clean captures; 1 noisy excluded)
- Top Gear **full-lap soft-corridor** fingerprint — two runway soft zones (~1015–1145 m, ~2290–2675 m)
- Captures that were saved under Albert Park by mistake were relocated to `top-gear-test-track/`
- All TA share codes **staged only** in `data/time-attack-codes.json` (`published: false`) — not on Track Codes / How To Use / Live Timing yet  
  - Albert Park `129783632`  
  - Autodromo Nazionale Monza `483419555`  
  - Autodromo Nazionale Monza Junior Course `163986603`  
  - Circuit de Monaco `173579476`  
  - Top Gear Test Track `156519500`  
  - Brands Hatch Circuit `108005006`  
  - Brands Hatch Indy Circuit `134791801`
- Collector UI: **driver mode** — Setup, Claim, drive, Troubleshooting; research tools behind `?lab=1`
- **Brands Hatch Indy** TA start fingerprint shipped (5 captures, 2 pit slots, 2 km layout window)
- **Brands Hatch Circuit (GP)** TA start fingerprint shipped (~3.9 km laps, 2 pit slots, 2 km layout window). First GP folder batch was Indy-length and was moved aside.
- **CD playtest green (2026-10-23):** Brands Hatch Circuit and Indy auto-ID as Time Attack with the correct layout name
- **Unlisted boards live** (How To Use / TA buttons unchanged):
  - https://doomsantos.github.io/eventlab-codes/live-timing.html
  - https://doomsantos.github.io/eventlab-codes/leaderboards.html
- Track filters on those pages: Albert Park, Monza, Monza Junior, Monaco, Top Gear, **Brands Hatch Circuit**, **Brands Hatch Indy Circuit**. Names-only file `data/time-attack-tracks.json` — pages never fetch share codes.
- **Track Codes live:** Brands Hatch Circuit + Indy EventLab With/Without Drivatars (5/15/25/50). Time Attack share codes still unpublished.

## NEXT

1. CD re-playtest: restart collector → open world must not appear on Who's Racing → load a **Time Attack** EventLab (not Track Codes) → clean laps should hit Live Timing / Leaderboards  
2. Hold public unveil until CD says **unveil Time Attack** (codes still `published: false`; How To Use / nav still “soon”)  
3. Optional: more TA tracks before unveil

## OPEN DEBT

- Microsoft OAuth deferred
- Default session end = midnight AEST (implemented; CD can override hour later)
- Banner ~1024px (upgrade when CD supplies)
- Public Live Timing / Leaderboards still teaser-gated in How To Use / nav until CD unveil (unlisted tester URLs are live)
- **Invites:** IG reel pre-signup → CD notes DMs → batch-mint + send codes on launch; reassess ongoing need after. IG auto-DM mint bot deferred (`docs/PRODUCT_BRIEF.md`)

## Commands

```powershell
python -m unittest discover -s collector -p "test_*.py" -v
python -m unittest discover -s server -p "test_*.py" -v
python -m server --port 8787
python -m collector
mint-invite.bat
```

API: https://dsr-eventlab-timing-production.up.railway.app  
Pages: https://doomsantos.github.io/eventlab-codes/  
Time Attack: https://doomsantos.github.io/eventlab-codes/leaderboard.html
