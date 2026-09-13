# Agent handover — DoomSantos Racing / Time Attack

## Copy-paste for a **new** Lead chat

```
You are Autonomous Lead Engineer. I am Creative Director.

OPERATING MODEL: C:\Users\clove\CursorProjects\Project Master Plan\AUTONOMOUS_LEAD_PLAYBOOK.md
Also follow this repo’s AGENTS.md / .cursorrules / PROJECT_ROADMAP.md / docs/PRODUCT_BRIEF.md / docs/TIME_ATTACK.md.

PRODUCT: DoomSantos Racing — EventLab Track Codes + Time Attack (PC collector → Railway API → Live Timing / Leaderboards)
WORKSPACE: C:\Users\clove\CursorProjects\DSR EventLab Codes Page

Use docs/agent-handover.md as LAST COMPLETED / NEXT if fresher than this message.

LAST COMPLETED: Doom fantasy / doom metal site theme live (banner + Track Codes / Time Attack titles + nav)
NEXT: Wait for CD TA EventLab codes/fingerprints → fingerprint TA starts → unveil Live Timing + Leaderboards; optional higher-res banner (≥1920px)
OPEN DEBT: TA fingerprints/codes not built yet; Microsoft OAuth deferred (docs/MICROSOFT_OAUTH_NOTES.md); default session end = midnight AEST unless CD overrides; banner currently ~1024px (upgrade when CD supplies)
```

## LAST COMPLETED

- Public doom-metal theme live
- Local test bats + Time Attack capture label
- Albert Park **TA offset-start fingerprint** + collector auto-detect (`mode=time_attack`)

## NEXT

1. Server: persist `mode` on uploads; filter public boards to TA-only  
2. CD playtest: restart TA event → confirm Mode column says Time Attack  
3. Unveil Live Timing / Leaderboards when ready  
4. Optional: higher-res banner

## OPEN DEBT

- Server `mode` column not built yet (collector already sends `mode` in upload payload)
- Microsoft OAuth deferred
- Default session end = midnight AEST unless CD overrides
- Banner ~1024px (upgrade when CD supplies)

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
