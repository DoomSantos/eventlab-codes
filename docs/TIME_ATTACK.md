# Time Attack — product decisions (SSOT)

**Brand display:** DoomSantos Racing (handle/URL `doomsantosracing` fine).  
**Product name:** Time Attack (replaces vague “live timing / leaderboard” public naming).  
**Status:** Spec locked 2026-09-13. Public **How To Use teaser** + nav shell shipped (`leaderboard.html`). Live Timing / Leaderboards stay gated until EventLab Time Attack routes + codes exist. Private lab (`board-lab.html`) + Railway API remain for testing.

Mockups (placeholder look): Track Codes | Time Attack → How To Use / Live Timing / Leaderboards.

---

## Site information architecture

| Nav | Page | Job |
|-----|------|-----|
| Track Codes | Existing codes catalogue | Share codes; later include Time Attack as a variant per track |
| Time Attack → **How To Use** | Explain mode + setup | What it is, special start/grid, codes, collector, invites, Data Out; only TA events count |
| Time Attack → **Live Timing** | Today’s session board | Best of today + expand today’s Clean laps; current players; session countdown |
| Time Attack → **Leaderboards** | Period / all-time board | 1 best lap per player × track × class; filters |
| (Later) Player profile | Full history | All stored Times Attack laps for that player |

**Subnav labels:** How To Use · Live Timing · Leaderboards (not “Living Timing”).

Until unveil: **How To Use teaser** under Time Attack — basic “how it will work,” no fragile specifics. Live Timing / Leaderboards labeled soon in subnav.

---

## Locked rules (CD)

| Topic | Decision |
|-------|----------|
| Session timezone | **AEST (UTC+10)** — session/day boundaries in AEST |
| Live Timing | Best Clean lap **today (AEST)** per driver (on TA tracks); expand = that driver’s **today** Clean laps (newest first) |
| Leaderboards | **1 best Clean lap per player per track per class**; Class filter = letter only (X R S2 S1 A B C D); columns show Class/PI + Car |
| Results filter | `Anytime` / `Today` / `This Week` / `This Month` / `This Year` → API windows `all` / `today` / `7d` / `30d` / `365d` |
| What counts | **Only Time Attack events** (offset-grid / fingerprintable starts). Other EventLab codes do not count. Must be clear in How To Use |
| Events | **One TA event per track**, typically **50 laps**; laps upload as they complete — players may quit early |
| Share codes | In **How To Use** (primary) + listed under Track Codes as **Time Attack** variant |
| Visibility | Live Timing + Leaderboards (+ profiles later) **public to view**; submit still via collector + invite |
| Auto-detect | Collector fingerprints TA offset-start; How To Use: “use these codes; the board knows” |
| Empty states | e.g. “No one on a Time Attack event right now” |
| Deep links | From Live Timing track name → How To Use / that track’s TA code |
| Nav shell | Track Codes \| Time Attack; TA subnav only under Time Attack |

---

## Engineering notes (not blocking unveil teaser)

- Persist `mode=time_attack` (or event id) on uploads once fingerprints exist; reject/ignore non-TA for public boards.
- **Who's Racing** is Time Attack only. Collector presence includes `mode`; `/v1/live` ignores open-world / other EventLab heartbeats (`is_race_on` is not enough). Session can arm from the live start path before lap 1 finishes.
- Auto-upload to the public board is Clean **Time Attack** laps only. Casual EventLab and open-world laps stay local.
- **Albert Park TA start fingerprint shipped** (`data/fingerprints/albert-park-time-attack-start.json`); collector auto-detects offset start and sets `mode=time_attack`.
- **Sticky TA session:** offset-start match arms the session; laps 2+ inherit `time_attack` (they restart at the normal line). Session clears when the lap counter drops (quit/restart/new event) or when a new lap 1 does **not** match the offset start. Only a fresh offset-start match re-arms — so “TA start lap → swap to another EventLab” does not keep counting.
- **Sticky layout:** the offset-start also locks the track name for the rest of the session. Laps 2+ of full Monza start at the normal line; the first 800 m looks like Junior Course, so re-ID would flip them. Same risk on Brands Hatch GP vs Indy.
- **Festival load:** open-world path + EventLab teleport onto the pit grid is still Time Attack. Matcher scores a new start window after **500 m+** jumps (Albert Park paddock→pits can be ~1300 m, below the integrity 1500 m ignore). The detector also drops the festival path when that teleport happens with the lap timer still near 0.
- **Monza TA start:** multi-slot variants (front/rear pit grid) in `autodromo-nazionale-monza-time-attack-start.json`. Matcher tries all track TA fingerprints; a match also sets the track name.
- **Monza Junior Course:** shares the pit exit with full Monza — short start matches both; an **800 m layout window** picks the correct track. Fingerprint: `autodromo-nazionale-monza-junior-course-time-attack-start.json`.
- **Monaco:** `circuit-de-monaco-time-attack-start.json` (multi-slot pit variants).
- **Top Gear Test Track:** TA start + full-lap fingerprint with **soft corridors** on the two airport-runway straights (~1.0–1.1 km and ~2.3–2.7 km). Wider training lines widen local match radius there only; tight sections stay strict.
- **Brands Hatch:** Indy and GP share the pit and the first ~1.4 km. TA start fingerprints use a **2 km layout window** (not Monza’s 800 m). `brands-hatch-indy-circuit-time-attack-start.json` (2 pit slots) and `brands-hatch-circuit-time-attack-start.json`. CD playtest 2026-10-23: both layouts auto-ID correctly.
- **Server persists `mode`** on `/v1/laps`; public `/v1/board` defaults to `mode=time_attack` only (`on_board` requires clean + time_attack).
- **Windows:** `/v1/board?window=` supports `today` (AEST midnight) / `24h` / `7d` / `30d` / `365d` / `all`; response includes `session` (AEST day + `ends_at`).
- **Leaderboards API:** `GET /v1/leaderboard` — 1 best Clean TA lap per player × track × class; `?class=R` letter filter; default `window=all`.
- Day bucket = AEST calendar date of `submitted_at`.
- Leaderboard class filter matches `class_name` only; display still `class_name + PI`.
- Profile pages use existing `/v1/history` (extend as needed).

---

## Open (minor — not blockers for teaser)

1. Exact AEST session end clock (default **midnight AEST** unless CD picks another hour).  
2. When first TA share codes + fingerprints are ready, unveil replaces teaser.  
   **Codes staged (not public):** see `data/time-attack-codes.json` (`published: false`).  
   Albert Park `129783632` · Monza `483419555` · Monza Junior `163986603` · Monaco `173579476` · Top Gear `156519500` · Brands Hatch Circuit `108005006` · Brands Hatch Indy `134791801`.
3. Profile URL shape (`/player/Name` vs query) — decide at build time.
