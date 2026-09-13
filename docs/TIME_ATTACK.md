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
- Day bucket = AEST calendar date of `submitted_at`.
- Leaderboard class filter matches `class_name` only; display still `class_name + PI`.
- Profile pages use existing `/v1/history` (extend as needed).

---

## Open (minor — not blockers for teaser)

1. Exact AEST session end clock (default **midnight AEST** unless CD picks another hour).  
2. When first TA share codes + fingerprints are ready, unveil replaces teaser.  
3. Profile URL shape (`/player/Name` vs query) — decide at build time.
